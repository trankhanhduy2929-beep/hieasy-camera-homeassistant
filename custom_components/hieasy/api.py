"""Async client for the cloud API used by HiEasy 8.1.2."""

from __future__ import annotations

import base64
import json
import logging
import random
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    APP_SN,
    APP_SOURCE,
    APP_VERSION,
    DEVICE_LIST_PATH,
    LOGIN_PATH,
    REGION_AUTO,
    REGION_ORDER,
    REGION_SERVERS,
    TOKEN_SECRET,
)
from .models import CloudDevice

_LOGGER = logging.getLogger(__name__)

_IPV4_RE = re.compile(
    r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])"
)
_PHONE_SEPARATORS_RE = re.compile(r"[\s().-]+")
_PHONE_ACCOUNT_RE = re.compile(r"(?:\+|00)?\d+")


def normalize_account(account: str) -> str:
    """Normalize Vietnamese phone accounts to the format used by HiEasy."""
    stripped = account.strip()
    compact = _PHONE_SEPARATORS_RE.sub("", stripped)
    if not _PHONE_ACCOUNT_RE.fullmatch(compact):
        return stripped

    if compact.startswith("+84"):
        compact = compact[3:]
    elif compact.startswith("0084"):
        compact = compact[4:]
    elif compact.startswith("84") and len(compact) in {11, 12}:
        compact = compact[2:]

    if compact.startswith("0") and len(compact) in {10, 11}:
        compact = compact[1:]

    if compact.isdigit() and len(compact) in {9, 10}:
        return compact
    return stripped


class HiEasyError(Exception):
    """Base exception for HiEasy API errors."""


class HiEasyCannotConnectError(HiEasyError):
    """Raised when no HiEasy cloud endpoint can be reached."""


class HiEasyInvalidAuthError(HiEasyError):
    """Raised when the account or password is rejected."""

    def __init__(
        self,
        message: str,
        *,
        region: str | None = None,
        code: int | None = None,
    ) -> None:
        """Initialize an authentication error with safe cloud metadata."""
        super().__init__(message)
        self.region = region
        self.code = code


class HiEasyApiError(HiEasyError):
    """Raised when the cloud returns an unexpected error."""


@dataclass(frozen=True, slots=True)
class LoginSession:
    """Successful cloud login details."""

    region: str
    token: str
    user_data: dict[str, Any]


def decrypt_ea_token(encrypted_token: str, account: str) -> str:
    """Decrypt the 3DES token used by Europe, America and YL servers."""
    if not encrypted_token:
        return ""

    key = (account + TOKEN_SECRET).encode("utf-8")[:24]
    if len(key) != 24:
        return ""

    try:
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, modes

        try:
            from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
        except ImportError:
            from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES

        decryptor = Cipher(TripleDES(key), modes.ECB()).decryptor()
        padded = decryptor.update(base64.b64decode(encrypted_token)) + decryptor.finalize()
        unpadder = padding.PKCS7(64).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""


class HiEasyCloudClient:
    """Client for login and device discovery through the HiEasy cloud."""

    def __init__(
        self,
        session: ClientSession,
        account: str,
        password: str,
        region: str = REGION_AUTO,
        *,
        request_timeout: float = 15.0,
    ) -> None:
        """Initialize the cloud client."""
        self._session = session
        self.account = normalize_account(account)
        self.password = password
        self.requested_region = region
        self.request_timeout = request_timeout
        self.region: str | None = None
        self.token = ""
        self.user_data: dict[str, Any] = {}
        self._mid = f"android{random.randrange(10000)}"

    async def async_login(self, *, force: bool = False) -> LoginSession:
        """Log in, probing all known regions when auto mode is selected."""
        if self.token and self.region and not force:
            return LoginSession(self.region, self.token, self.user_data)

        regions: Iterable[str]
        if self.requested_region == REGION_AUTO:
            regions = REGION_ORDER
        else:
            regions = (self.requested_region,)

        connection_errors: list[str] = []
        auth_errors: list[HiEasyInvalidAuthError] = []
        api_errors: list[HiEasyApiError] = []

        for region in regions:
            try:
                login = await self._async_login_region(region)
            except HiEasyCannotConnectError as err:
                connection_errors.append(f"{region}: {err}")
                continue
            except HiEasyInvalidAuthError as err:
                auth_errors.append(err)
                continue
            except HiEasyApiError as err:
                api_errors.append(err)
                if self.requested_region != REGION_AUTO:
                    raise
                continue

            self.region = login.region
            self.token = login.token
            self.user_data = login.user_data
            return login

        self.token = ""
        self.region = None
        password_error = next(
            (error for error in auth_errors if error.code == 2011),
            None,
        )
        if password_error is not None:
            raise password_error
        if auth_errors and not api_errors:
            raise auth_errors[-1]
        if api_errors:
            raise api_errors[-1]
        raise HiEasyCannotConnectError(
            "; ".join(connection_errors) or "Không kết nối được máy chủ HiEasy"
        )

    async def _async_login_region(self, region: str) -> LoginSession:
        """Attempt one regional login."""
        try:
            root, prefix, encrypted_header = REGION_SERVERS[region]
        except KeyError as err:
            raise HiEasyApiError(f"Vùng HiEasy không hợp lệ: {region}") from err

        payload = {
            "account": self.account,
            "pwd": self.password,
            "sn": APP_SN,
            "mid": self._mid,
            "source": APP_SOURCE,
            "clientVersion": APP_VERSION,
        }
        status, headers, data = await self._async_request_json(
            "POST", f"{root}{prefix}{LOGIN_PATH}", json_body=payload
        )
        code = _response_code(data)
        if status in (401, 403) or code in {2011, 2101, 2102}:
            message = _response_message(data) or "Đăng nhập thất bại"
            raise HiEasyInvalidAuthError(
                message,
                region=region,
                code=code,
            )
        if not 200 <= status < 300:
            raise HiEasyApiError(
                f"Máy chủ {region} trả HTTP {status}: {_response_message(data)}"
            )
        if code is not None and code not in {0, 200}:
            raise HiEasyApiError(
                f"Máy chủ {region} trả mã {code}: {_response_message(data)}"
            )

        body_token = _extract_token(data)
        header_token = headers.get("token", "")
        token = body_token
        if encrypted_header and header_token:
            token = decrypt_ea_token(header_token, self.account)
            if not token and "-" in header_token:
                token = header_token
        elif header_token and not token:
            token = header_token

        if not token:
            raise HiEasyApiError(f"Máy chủ {region} không trả token")

        user_data = _extract_user_data(data)
        return LoginSession(region, token, user_data)

    async def async_get_devices(self) -> list[CloudDevice]:
        """Return devices linked to the authenticated account."""
        if not self.token or not self.region:
            await self.async_login()
        return await self._async_get_devices_once(retry_auth=True)

    async def _async_get_devices_once(self, *, retry_auth: bool) -> list[CloudDevice]:
        """Fetch the cloud device list, optionally retrying expired auth once."""
        assert self.region is not None
        root, prefix, _encrypted_header = REGION_SERVERS[self.region]
        status, _headers, data = await self._async_request_json(
            "GET",
            f"{root}{prefix}{DEVICE_LIST_PATH}",
            headers={"token": self.token},
        )
        code = _response_code(data)
        if status in (401, 403) or code in {2308, 2309}:
            if retry_auth:
                await self.async_login(force=True)
                return await self._async_get_devices_once(retry_auth=False)
            raise HiEasyInvalidAuthError("Phiên đăng nhập HiEasy đã hết hạn")
        if not 200 <= status < 300:
            raise HiEasyApiError(
                f"Không lấy được danh sách thiết bị, HTTP {status}: "
                f"{_response_message(data)}"
            )
        if code is not None and code not in {0, 200}:
            raise HiEasyApiError(
                f"Không lấy được danh sách thiết bị, mã {code}: "
                f"{_response_message(data)}"
            )

        entries = _extract_entries(data)
        return [device for item in entries if (device := parse_cloud_device(item))]

    async def _async_request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Mapping[str, str], dict[str, Any]]:
        """Perform one JSON request with consistent error handling."""
        try:
            async with self._session.request(
                method,
                url,
                json=json_body,
                headers=headers,
                timeout=ClientTimeout(total=self.request_timeout),
            ) as response:
                text = await response.text()
                response_headers = {
                    str(key).lower(): str(value)
                    for key, value in response.headers.items()
                }
                if not text.strip():
                    data: dict[str, Any] = {}
                else:
                    decoded = json.loads(text)
                    data = decoded if isinstance(decoded, dict) else {"data": decoded}
                return response.status, response_headers, data
        except (ClientError, TimeoutError, OSError) as err:
            raise HiEasyCannotConnectError(str(err)) from err
        except json.JSONDecodeError as err:
            raise HiEasyApiError(f"Phản hồi JSON không hợp lệ từ {url}") from err


def parse_cloud_device(raw: Mapping[str, Any]) -> CloudDevice | None:
    """Convert one device-list entry into a stable model."""
    item = dict(raw)
    did = _string(_first(item, "did", "DID", "deviceId", "uuid"))
    if not did:
        return None

    nested = _nested_maps(item)
    name = _string(_first(item, "alias", "nickName", "name")) or did
    username = _string(_first(item, "username", "userName", "user")) or "admin"
    password = _string(_first(item, "pwd", "password", "passwd"))
    mac = _optional_string(_first_any(nested, "mac", "macAddress"))
    serial = _optional_string(
        _first_any(nested, "deviceSn", "serialNum", "serial", "sn")
    )
    model = _optional_string(
        _first_any(nested, "model", "deviceName", "modelName", "productName")
    )
    firmware = _optional_string(
        _first_any(
            nested,
            "version",
            "firmware",
            "firmwareVersion",
            "softWareVersion",
            "customerVersion",
        )
    )
    channel_count = _coerce_int(
        _first_any(
            nested,
            "channelSize",
            "channelCount",
            "videoInputChannels",
            "deviceChannelCount",
        ),
        default=1,
    )
    channel_count = min(max(channel_count, 1), 32)

    battery = _coerce_float(
        _first_any(nested, "batteryPower", "BatteryPower", "battery", "power")
    )
    signal = _coerce_float(
        _first_any(
            nested,
            "signalIntensity",
            "SignalIntensity",
            "signalVal",
            "signal",
            "wifiQuality",
        )
    )

    return CloudDevice(
        did=did,
        name=name,
        username=username,
        password=password,
        mac=mac,
        serial=serial,
        model=model,
        firmware=firmware,
        device_type=_optional_string(_first_any(nested, "deviceType")),
        dtype=_optional_string(_first(item, "dtype")),
        channel_count=channel_count,
        cloud_status=_cloud_status(nested),
        battery=battery,
        signal=signal,
        iccid=_optional_string(_first_any(nested, "iccid")),
        imei=_optional_string(_first_any(nested, "imei")),
        local_hints=tuple(_extract_local_hints(nested)),
        raw=item,
    )


def _response_code(data: Mapping[str, Any]) -> int | None:
    value = data.get("code")
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _response_message(data: Mapping[str, Any]) -> str:
    for key in ("error", "message", "msg", "description"):
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _extract_token(data: Mapping[str, Any]) -> str:
    payload = _decode_json_value(data.get("data"))
    if isinstance(payload, Mapping):
        value = payload.get("token")
        if value:
            return str(value)
    value = data.get("token")
    return str(value) if value else ""


def _extract_user_data(data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _decode_json_value(data.get("data"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _extract_entries(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Locate the entries array across both CN/SGP and EU/US response shapes."""
    queue: list[Any] = [data]
    visited: set[int] = set()
    while queue:
        current = _decode_json_value(queue.pop(0))
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        if isinstance(current, Mapping):
            for key in ("entries", "devices", "deviceList", "list"):
                value = _decode_json_value(current.get(key))
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, Mapping)]
            queue.extend(current.values())
        elif isinstance(current, list):
            if all(isinstance(item, Mapping) for item in current):
                return current
            queue.extend(current)
    return []


def _decode_json_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def _nested_maps(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = [raw]
    for value in raw.values():
        decoded = _decode_json_value(value)
        if isinstance(decoded, Mapping):
            maps.append(decoded)
    return maps


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, "", "null"):
            return value
    return None


def _first_any(mappings: Iterable[Mapping[str, Any]], *keys: str) -> Any:
    for mapping in mappings:
        value = _first(mapping, *keys)
        if value not in (None, "", "null"):
            return value
    return None


def _string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _optional_string(value: Any) -> str | None:
    result = _string(value)
    return result if result and result.lower() != "null" else None


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cloud_status(mappings: Iterable[Mapping[str, Any]]) -> Any:
    """Mirror the APK: status == 1 or serverStatus == 1 means online."""
    status = _first_any(mappings, "status", "online")
    server_status = _first_any(mappings, "serverStatus")
    for value in (status, server_status):
        if value is True or str(value).strip().lower() in {"1", "online", "true"}:
            return 1
    return status if status is not None else server_status


def _extract_local_hints(mappings: Iterable[Mapping[str, Any]]) -> list[str]:
    hints: list[str] = []
    hint_keys = {
        "host",
        "ip",
        "ipaddress",
        "localip",
        "lanip",
        "deviceip",
        "address",
        "url",
    }
    for mapping in mappings:
        for key, value in mapping.items():
            if str(key).lower() not in hint_keys or not isinstance(value, str):
                continue
            for host in _IPV4_RE.findall(value):
                if host not in hints:
                    hints.append(host)
    return hints
