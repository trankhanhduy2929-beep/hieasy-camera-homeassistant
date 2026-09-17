"""LAN discovery and local protocol support for HiEasy cameras."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aiohttp import BasicAuth, ClientError, ClientSession, ClientTimeout

from .const import (
    DEFAULT_MAX_SCAN_HOSTS,
    DEFAULT_RTSP_PATHS,
    DEFAULT_RTSP_PORTS,
    DEFAULT_SCAN_PORTS,
    DEFAULT_SCAN_TIMEOUT,
    ENDPOINT_ALARM_OUT,
    ENDPOINT_DEVICE_INFO,
    ENDPOINT_INDICATOR,
    ENDPOINT_LIGHT_CONTROL,
    ENDPOINT_NETWORK_PORT,
    ENDPOINT_NIGHT_VISION,
    ENDPOINT_PTZ_CAP,
    ENDPOINT_RUNNING_INFO,
    STREAM_MAIN,
    STREAM_SUB,
    STREAM_THIRD,
)
from .models import CloudDevice, DeviceRuntime, LanConnection
from .protocol import (
    HiEasyXmlError,
    build_digest_authorization,
    extract_rtsp_uri,
    flatten_xml,
    identities_match,
    mutate_first_alias,
    normalize_rtsp_uri,
    parse_device_identity,
    parse_digest_challenge,
    parse_onvif_media_url,
    parse_onvif_profiles,
    parse_onvif_stream_uri,
    parse_port_config,
    parse_ws_discovery_urls,
)

_LOGGER = logging.getLogger(__name__)

_ONVIF_PROBE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
 xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
 <e:Header>
  <w:MessageID>uuid:hi-easy-discovery</w:MessageID>
  <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
  <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
 </e:Header>
 <e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>
</e:Envelope>"""

_ONVIF_NS = "http://www.onvif.org/ver10/media/wsdl"
_SOAP_ENV = "http://www.w3.org/2003/05/soap-envelope"
_HOSTNAME_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\Z"
)
_MAX_MANUAL_HOSTS = 64
_MAX_RTSP_PATHS = 16
_MAX_RTSP_PROBES = 48
_MAX_RTSP_BODY = 128 * 1024


class LanError(Exception):
    """Base class for local discovery errors."""


class LanRequestError(LanError):
    """Raised for a local HTTP error."""

    def __init__(self, status: int, message: str, headers: Mapping[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.headers = dict(headers or {})


@dataclass(frozen=True, slots=True)
class LanCandidate:
    """A possible local camera endpoint."""

    scheme: str
    host: str
    port: int
    source: str = "scan"
    service_url: str | None = None

    @property
    def key(self) -> str:
        host = f"[{self.host}]" if ":" in self.host and not self.host.startswith("[") else self.host
        return f"{self.scheme}://{host}:{self.port}"

    @property
    def base_url(self) -> str:
        return self.key


@dataclass(frozen=True, slots=True)
class LanResponse:
    """Small response object independent of aiohttp response lifetime."""

    status: int
    headers: Mapping[str, str]
    text: str


@dataclass(frozen=True, slots=True)
class RtspResponse:
    """Parsed response from a bounded RTSP control request."""

    status: int
    headers: Mapping[str, str]
    body: bytes


class LanHttpClient:
    """HTTP client with Basic and common Digest authentication support."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout: float = DEFAULT_SCAN_TIMEOUT,
    ) -> None:
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._digest_challenge: dict[str, str] | None = None

    async def async_request(
        self,
        method: str,
        path_or_url: str,
        *,
        body: str | bytes | None = None,
        headers: Mapping[str, str] | None = None,
        expected_status: Iterable[int] = (200, 201, 202, 204),
    ) -> LanResponse:
        """Make one authenticated request."""
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}/{path_or_url.lstrip('/')}"
        request_headers = {str(key): str(value) for key, value in (headers or {}).items()}
        if self._digest_challenge:
            target = urlsplit(url).path or "/"
            if urlsplit(url).query:
                target += f"?{urlsplit(url).query}"
            request_headers["Authorization"] = build_digest_authorization(
                self._digest_challenge,
                method,
                target,
                self.username,
                self.password,
            )
        response = await self._async_request_once(method, url, body, request_headers)

        if response.status == 401:
            challenge_header = response.headers.get("www-authenticate", "")
            challenge = parse_digest_challenge(challenge_header)
            if challenge:
                self._digest_challenge = challenge
                target = urlsplit(url).path or "/"
                if urlsplit(url).query:
                    target += f"?{urlsplit(url).query}"
                request_headers["Authorization"] = build_digest_authorization(
                    challenge,
                    method,
                    target,
                    self.username,
                    self.password,
                )
                response = await self._async_request_once(method, url, body, request_headers)
            elif self.username or self.password:
                request_headers.pop("Authorization", None)
                request_headers["Authorization"] = BasicAuth(
                    self.username, self.password, encoding="utf-8"
                ).encode()
                response = await self._async_request_once(method, url, body, request_headers)

        if response.status not in expected_status:
            raise LanRequestError(
                response.status,
                f"HTTP {response.status} từ {url}",
                response.headers,
            )
        return response

    async def async_get_xml(self, path_or_url: str) -> str:
        """GET an XML endpoint."""
        response = await self.async_request("GET", path_or_url)
        return response.text

    async def async_put_xml(self, path_or_url: str, xml_text: str) -> str:
        """PUT XML to a device endpoint."""
        response = await self.async_request(
            "PUT",
            path_or_url,
            body=xml_text,
            headers={"Content-Type": "text/xml; charset=UTF-8"},
        )
        return response.text

    async def _async_request_once(
        self,
        method: str,
        url: str,
        body: str | bytes | None,
        headers: Mapping[str, str],
    ) -> LanResponse:
        try:
            async with self.session.request(
                method,
                url,
                data=body,
                headers=dict(headers),
                timeout=ClientTimeout(total=self.timeout),
            ) as response:
                text = await response.text()
                return LanResponse(
                    response.status,
                    {str(key).lower(): str(value) for key, value in response.headers.items()},
                    text,
                )
        except (ClientError, TimeoutError, OSError) as err:
            raise LanError(str(err)) from err


async def async_ws_discover(timeout: float = 2.0) -> list[LanCandidate]:
    """Discover ONVIF services using WS-Discovery multicast."""
    loop = asyncio.get_running_loop()
    urls: set[str] = set()
    transport: asyncio.DatagramTransport | None = None

    class _Protocol(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, _addr: tuple[str, int]) -> None:
            urls.update(parse_ws_discovery_urls(data.decode("utf-8", "ignore")))

        def error_received(self, exc: Exception) -> None:
            _LOGGER.debug("WS-Discovery lỗi: %s", exc)

    try:
        transport, _protocol = await loop.create_datagram_endpoint(
            _Protocol,
            local_addr=("0.0.0.0", 0),
        )
        transport.sendto(_ONVIF_PROBE.encode("utf-8"), ("239.255.255.250", 3702))
        await asyncio.sleep(max(timeout, 0.1))
    except (OSError, asyncio.TimeoutError) as err:
        _LOGGER.debug("Không tạo được WS-Discovery socket: %s", err)
    finally:
        if transport is not None:
            transport.close()

    candidates: list[LanCandidate] = []
    for url in sorted(urls):
        try:
            parts = urlsplit(url)
            if not parts.hostname:
                continue
            candidates.append(
                LanCandidate(
                    parts.scheme or "http",
                    parts.hostname,
                    parts.port or (443 if parts.scheme == "https" else 80),
                    "ws-discovery",
                    url,
                )
            )
        except ValueError:
            continue
    return _dedupe_candidates(candidates)


def parse_scan_ports(value: str | Sequence[int] | None) -> list[int]:
    """Parse a comma-separated port list safely."""
    if value is None:
        value = DEFAULT_SCAN_PORTS
    return _parse_ports(value) or [80]


def parse_rtsp_ports(value: str | Sequence[int] | None) -> list[int]:
    """Parse RTSP ports with a protocol-appropriate fallback."""
    if value is None:
        value = DEFAULT_RTSP_PORTS
    return _parse_ports(value) or [554]


def _parse_ports(value: str | Sequence[int]) -> list[int]:
    """Parse one bounded list of TCP ports."""
    if isinstance(value, str):
        values: Iterable[object] = value.split(",")
    else:
        values = value
    ports: list[int] = []
    for item in values:
        try:
            port = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535 and port not in ports:
            ports.append(port)
    return ports


def parse_scan_hosts(value: str | Sequence[str] | None) -> list[str]:
    """Parse explicit IP addresses or hostnames without accepting URLs."""
    if isinstance(value, str):
        values = re.split(r"[,\s]+", value)
    elif value:
        values = [str(item) for item in value]
    else:
        values = []

    hosts: list[str] = []
    for item in values:
        host = item.strip().strip("[]")
        if not _is_valid_host(host) or host.lower() in {item.lower() for item in hosts}:
            continue
        hosts.append(host)
        if len(hosts) >= _MAX_MANUAL_HOSTS:
            break
    return hosts


def parse_rtsp_paths(value: str | Sequence[str] | None) -> list[str]:
    """Parse a bounded list of relative RTSP path templates."""
    if value is None:
        value = DEFAULT_RTSP_PATHS
    if isinstance(value, str):
        values: Iterable[object] = re.split(r"[,\n]+", value)
    else:
        values = value

    paths: list[str] = []
    for item in values:
        path = str(item).strip()
        if (
            not path.startswith("/")
            or "://" in path
            or any(ord(character) <= 0x20 for character in path)
            or len(path) > 256
            or path in paths
        ):
            continue
        paths.append(path)
        if len(paths) >= _MAX_RTSP_PATHS:
            break
    if paths:
        return paths
    return ["/live/ch{channel}"]


def expand_rtsp_path(template: str, channel: int, stream: int) -> str:
    """Expand supported placeholders in one safe RTSP path template."""
    profile = {STREAM_MAIN: "main", STREAM_SUB: "sub", STREAM_THIRD: "third"}.get(
        stream,
        str(stream),
    )
    return (
        template.replace("{channel02}", f"{channel:02d}")
        .replace("{channel}", str(channel))
        .replace("{stream}", str(stream))
        .replace("{subtype}", str(max(stream - 1, 0)))
        .replace("{profile}", profile)
    )


def derive_scan_networks(configured: str | Sequence[str] | None) -> list[ipaddress.IPv4Network]:
    """Return configured networks, or conservative /24 networks from local interfaces."""
    values: list[str] = []
    if isinstance(configured, str):
        values = [part.strip() for part in re.split(r"[,\s]+", configured) if part.strip()]
    elif configured:
        values = [str(part).strip() for part in configured if str(part).strip()]

    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            continue
        if isinstance(network, ipaddress.IPv4Network) and not network.is_loopback:
            networks.append(network)
    if networks:
        return _dedupe_networks(networks)

    local_ips: set[str] = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            local_ips.add(item[4][0])
    except OSError:
        pass
    try:
        with open("/proc/net/route", encoding="ascii") as route_file:
            for line in route_file.readlines()[1:]:
                parts = line.split()
                if len(parts) > 2 and parts[1] != "00000000":
                    raw_destination = int(parts[1], 16)
                    raw_mask = int(parts[7], 16) if len(parts) > 7 else 0xFFFFFF00
                    destination = socket.inet_ntoa(raw_destination.to_bytes(4, "little"))
                    mask = socket.inet_ntoa(raw_mask.to_bytes(4, "little"))
                    local_ips.add(str(ipaddress.ip_network(f"{destination}/{mask}", strict=False).network_address))
    except (OSError, ValueError):
        pass

    for ip_text in local_ips:
        try:
            address = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv4Address) and not address.is_loopback:
            networks.append(ipaddress.ip_network(f"{address}/24", strict=False))
    return _dedupe_networks(networks)


def iter_scan_candidates(
    networks: Iterable[ipaddress.IPv4Network],
    ports: Iterable[int],
    *,
    max_hosts: int = DEFAULT_MAX_SCAN_HOSTS,
    rtsp_ports: Iterable[int] = (),
) -> list[LanCandidate]:
    """Expand networks into bounded HTTP/ONVIF and RTSP candidates."""
    candidates: list[LanCandidate] = []
    count = 0
    http_ports = tuple(ports)
    media_ports = tuple(rtsp_ports)
    for network in networks:
        for host in network.hosts():
            if count >= max_hosts:
                return _dedupe_candidates(candidates)
            count += 1
            for port in http_ports:
                candidates.append(LanCandidate("http", str(host), port, "scan"))
            for port in media_ports:
                candidates.append(LanCandidate("rtsp", str(host), port, "scan"))
    return _dedupe_candidates(candidates)


async def async_discover_devices(
    session: ClientSession,
    devices: Sequence[CloudDevice],
    *,
    discover_lan: bool = True,
    hosts: str | Sequence[str] | None = None,
    networks: str | Sequence[str] | None = None,
    scan_ports: str | Sequence[int] | None = None,
    rtsp_ports: str | Sequence[int] | None = None,
    rtsp_paths: str | Sequence[str] | None = None,
    scan_timeout: float = DEFAULT_SCAN_TIMEOUT,
    max_scan_hosts: int = DEFAULT_MAX_SCAN_HOSTS,
    max_channels: int = 8,
) -> dict[str, LanConnection]:
    """Discover and pair local endpoints with cloud devices."""
    if not devices:
        return {}

    http_ports = parse_scan_ports(scan_ports)
    media_ports = parse_rtsp_ports(rtsp_ports)
    media_paths = parse_rtsp_paths(rtsp_paths)
    candidates: list[LanCandidate] = []
    if discover_lan:
        try:
            candidates.extend(await async_ws_discover(timeout=2.0))
        except (OSError, RuntimeError, asyncio.TimeoutError) as err:  # pragma: no cover
            _LOGGER.debug("WS-Discovery thất bại: %s", err)
    candidates.extend(
        _candidates_for_hosts(
            parse_scan_hosts(hosts),
            http_ports,
            media_ports,
            source="manual",
        )
    )
    for device in devices:
        candidates.extend(
            _candidates_from_hints(device.local_hints, http_ports, media_ports)
        )
    candidates = _dedupe_candidates(candidates)

    matched: dict[str, LanConnection] = {}

    async def match_candidates(batch: Sequence[LanCandidate]) -> None:
        remaining = [
            device for device in devices if device.unique_id not in matched
        ]
        if not remaining or not batch:
            return
        matched.update(
            await _async_match_candidates(
                session,
                remaining,
                batch,
                timeout=scan_timeout,
                max_channels=max_channels,
                rtsp_paths=media_paths,
            )
        )

    await match_candidates(
        [candidate for candidate in candidates if candidate.scheme != "rtsp"]
    )
    initial_rtsp = [candidate for candidate in candidates if candidate.scheme == "rtsp"]
    if initial_rtsp and len(matched) < len(devices):
        await match_candidates(
            await _async_filter_open_candidates(
                initial_rtsp,
                timeout=min(max(scan_timeout / 2, 0.15), 0.5),
            )
        )

    if discover_lan and len(matched) < len(devices):
        scan_networks = await asyncio.to_thread(derive_scan_networks, networks)
        scan_http_candidates = iter_scan_candidates(
            scan_networks,
            http_ports,
            max_hosts=max_scan_hosts,
        )
        await match_candidates(
            await _async_filter_open_candidates(
                scan_http_candidates,
                timeout=min(max(scan_timeout / 2, 0.15), 0.5),
            )
        )

        if len(matched) < len(devices):
            scan_rtsp_candidates = iter_scan_candidates(
                scan_networks,
                (),
                max_hosts=max_scan_hosts,
                rtsp_ports=media_ports,
            )
            await match_candidates(
                await _async_filter_open_candidates(
                    scan_rtsp_candidates,
                    timeout=min(max(scan_timeout / 2, 0.15), 0.5),
                )
            )
    return matched


async def _async_match_candidates(
    session: ClientSession,
    devices: Sequence[CloudDevice],
    candidates: Sequence[LanCandidate],
    *,
    timeout: float,
    max_channels: int,
    rtsp_paths: Sequence[str],
) -> dict[str, LanConnection]:
    """Probe candidates concurrently and retain the best match per device."""
    if not devices or not candidates:
        return {}
    semaphore = asyncio.Semaphore(24)
    results: list[tuple[CloudDevice, LanCandidate, LanConnection]] = []

    async def probe(device: CloudDevice, candidate: LanCandidate) -> None:
        async with semaphore:
            try:
                connection = await async_probe_candidate(
                    session,
                    device,
                    candidate,
                    timeout=timeout,
                    max_channels=max_channels,
                    rtsp_paths=rtsp_paths,
                )
            except (LanError, HiEasyXmlError, OSError) as err:
                _LOGGER.debug("Probe %s voor %s mislukt: %s", candidate.key, device.did, err)
                return
            if connection is not None:
                results.append((device, candidate, connection))

    tasks = [
        asyncio.create_task(probe(device, candidate))
        for device in devices
        for candidate in candidates
        if candidate.source != "cloud-hint"
        or candidate.host.lower()
        in {hint.strip().strip("[]").lower() for hint in device.local_hints}
    ]
    if tasks:
        await asyncio.gather(*tasks)

    matched: dict[str, LanConnection] = {}
    source_priority = {
        "existing": 0,
        "manual": 1,
        "cloud-hint": 2,
        "ws-discovery": 3,
        "scan": 4,
    }
    results.sort(
        key=lambda item: (
            source_priority.get(item[1].source, 9),
            -len(item[2].streams),
            item[0].unique_id,
            item[1].key,
        )
    )
    used_candidates: set[str] = set()
    for device, _candidate, connection in results:
        if device.unique_id in matched or _candidate.key in used_candidates:
            continue
        matched[device.unique_id] = connection
        used_candidates.add(_candidate.key)
    return matched


async def async_probe_candidate(
    session: ClientSession,
    device: CloudDevice,
    candidate: LanCandidate,
    *,
    timeout: float = DEFAULT_SCAN_TIMEOUT,
    max_channels: int = 8,
    rtsp_paths: str | Sequence[str] | None = None,
) -> LanConnection | None:
    """Probe proprietary CGI first, then fall back to ONVIF."""
    if candidate.scheme == "rtsp":
        return await _async_probe_rtsp(
            device,
            candidate,
            parse_rtsp_paths(rtsp_paths),
            timeout=timeout,
            max_channels=max_channels,
        )

    client = LanHttpClient(
        session,
        candidate.base_url,
        device.username,
        device.password,
        timeout=timeout,
    )
    port_xml: str | None = None
    try:
        port_xml = await client.async_get_xml(ENDPOINT_NETWORK_PORT)
    except LanError:
        pass

    if port_xml:
        ports = parse_port_config(port_xml)
        command_port = ports.get("command") or candidate.port
        media_port = ports.get("media")
        command_client = client
        if command_port != candidate.port:
            command_client = LanHttpClient(
                session,
                f"{candidate.scheme}://{candidate.host}:{command_port}",
                device.username,
                device.password,
                timeout=timeout,
            )
        try:
            info_xml = await command_client.async_get_xml(ENDPOINT_DEVICE_INFO)
        except LanError:
            info_xml = ""
        identity = parse_device_identity(info_xml) if info_xml else {}
        if identity and not identities_match(device, identity):
            return None

        connection = LanConnection(
            host=candidate.host,
            http_port=candidate.port,
            scheme=candidate.scheme,
            command_port=command_port,
            media_port=media_port,
            transport="lan_rtsp",
            identity=identity,
            online=True,
        )
        connection.xml[ENDPOINT_NETWORK_PORT] = port_xml
        if info_xml:
            connection.xml[ENDPOINT_DEVICE_INFO] = info_xml
            connection.values.update(
                {f"{ENDPOINT_DEVICE_INFO}:{key}": value for key, value in flatten_xml(info_xml).items()}
            )
        await _async_fetch_local_state(command_client, connection, device, max_channels)
        if connection.streams or info_xml or candidate.source != "scan":
            return connection

    onvif_url = candidate.service_url or f"{candidate.base_url}/onvif/device_service"
    try:
        connection = await _async_probe_onvif(
            session,
            device,
            candidate,
            onvif_url,
            timeout=timeout,
            max_channels=max_channels,
        )
    except LanError:
        return None
    return connection


async def _async_fetch_local_state(
    client: LanHttpClient,
    connection: LanConnection,
    device: CloudDevice,
    max_channels: int,
) -> None:
    """Fetch common settings and all practical stream profiles."""
    optional_paths = (
        ENDPOINT_RUNNING_INFO,
        ENDPOINT_INDICATOR,
        ENDPOINT_NIGHT_VISION,
        ENDPOINT_LIGHT_CONTROL,
        ENDPOINT_PTZ_CAP,
        ENDPOINT_ALARM_OUT,
    )
    async def get_optional(path: str) -> tuple[str, str] | None:
        try:
            return path, await client.async_get_xml(path)
        except LanError:
            return None

    optional_results = await asyncio.gather(*(get_optional(path) for path in optional_paths))
    for result in optional_results:
        if result is None:
            continue
        path, xml_text = result
        connection.xml[path] = xml_text
        connection.values.update(
            {f"{path}:{key}": value for key, value in flatten_xml(xml_text).items()}
        )
        if path == ENDPOINT_PTZ_CAP:
            flattened = flatten_xml(xml_text)
            support = flattened.get("support")
            connection.supports_ptz = str(support).lower() in {"true", "1", "yes"}

    channels = min(max(device.channel_count, 1), max_channels)
    for channel in range(1, channels + 1):
        try:
            motion_xml = await client.async_get_xml(f"/Pictures/{channel}/MoveTrack")
        except LanError:
            motion_xml = ""
        if motion_xml:
            path = f"/Pictures/{channel}/MoveTrack"
            connection.xml[path] = motion_xml
            connection.values.update(
                {f"{path}:{key}": value for key, value in flatten_xml(motion_xml).items()}
            )
        for stream in (STREAM_MAIN, STREAM_SUB, STREAM_THIRD):
            path = f"/Streams/{channel}/{stream}"
            try:
                stream_xml = await client.async_get_xml(path)
            except LanError:
                continue
            connection.xml[path] = stream_xml
            uri = extract_rtsp_uri(stream_xml)
            if uri:
                connection.streams[(channel, stream)] = normalize_rtsp_uri(
                    uri,
                    connection.host,
                    connection.media_port,
                    device.username,
                    device.password,
                )
            connection.values.update(
                {f"{path}:{key}": value for key, value in flatten_xml(stream_xml).items()}
            )


def iter_rtsp_probes(
    templates: Sequence[str],
    channel_count: int,
    *,
    max_channels: int = 8,
) -> list[tuple[int, int, str]]:
    """Expand RTSP templates into a bounded, deduplicated probe order."""
    probes: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    channels = min(max(channel_count, 1), max_channels)
    for channel in range(1, channels + 1):
        for stream in (STREAM_MAIN, STREAM_SUB, STREAM_THIRD):
            for template in templates:
                path = expand_rtsp_path(template, channel, stream)
                if path in seen:
                    continue
                seen.add(path)
                probes.append((channel, stream, path))
                if len(probes) >= _MAX_RTSP_PROBES:
                    return probes
    return probes


async def _async_probe_rtsp(
    device: CloudDevice,
    candidate: LanCandidate,
    paths: Sequence[str],
    *,
    timeout: float,
    max_channels: int,
) -> LanConnection | None:
    """Validate direct RTSP paths using the credentials from the cloud account."""
    auth_state: dict[str, Any] = {}
    try:
        options = await _async_rtsp_request_authenticated(
            candidate,
            "OPTIONS",
            "/",
            device.username,
            device.password,
            auth_state,
            timeout=timeout,
        )
    except LanError:
        return None
    if options.status == 401:
        return None

    streams: dict[tuple[int, int], str] = {}
    for channel, stream, path in iter_rtsp_probes(
        paths,
        device.channel_count,
        max_channels=max_channels,
    ):
        if (channel, stream) in streams:
            continue
        try:
            response = await _async_rtsp_request_authenticated(
                candidate,
                "DESCRIBE",
                path,
                device.username,
                device.password,
                auth_state,
                timeout=timeout,
            )
        except LanError:
            continue
        if response.status == 401:
            break
        stream_uri = _validated_rtsp_location(candidate, response, path)
        if stream_uri is None:
            continue
        streams[(channel, stream)] = normalize_rtsp_uri(
            stream_uri,
            candidate.host,
            candidate.port,
            device.username,
            device.password,
        )

    if not streams:
        return None
    return LanConnection(
        host=candidate.host,
        http_port=None,
        scheme="rtsp",
        media_port=candidate.port,
        transport="rtsp_scan",
        streams=streams,
        online=True,
    )


def _validated_rtsp_location(
    candidate: LanCandidate,
    response: RtspResponse,
    requested_path: str,
) -> str | None:
    """Return a same-host RTSP URI after a successful DESCRIBE."""
    if response.status == 200:
        return requested_path
    if response.status not in {301, 302, 307, 308}:
        return None
    location = response.headers.get("location")
    if not location:
        return None
    parts = urlsplit(location)
    if parts.scheme.lower() != "rtsp" or not parts.hostname:
        return None
    if parts.hostname.lower() != candidate.host.lower():
        return None
    if parts.port not in {None, candidate.port}:
        return None
    return location


async def _async_rtsp_request_authenticated(
    candidate: LanCandidate,
    method: str,
    path_or_uri: str,
    username: str,
    password: str,
    auth_state: dict[str, Any],
    *,
    timeout: float,
) -> RtspResponse:
    """Send an RTSP request and retry once with Basic or Digest auth."""
    uri = _rtsp_uri(candidate, path_or_uri)
    authorization = _rtsp_authorization(auth_state, method, uri, username, password)
    response = await _async_rtsp_request(
        candidate,
        method,
        uri,
        authorization=authorization,
        timeout=timeout,
    )
    if response.status != 401 or not username:
        return response

    challenge_header = response.headers.get("www-authenticate", "")
    challenge = parse_digest_challenge(challenge_header)
    auth_state.clear()
    if challenge:
        auth_state["digest"] = challenge
    elif challenge_header.lower().startswith("basic"):
        auth_state["basic"] = True
    else:
        return response

    authorization = _rtsp_authorization(auth_state, method, uri, username, password)
    if not authorization:
        return response
    return await _async_rtsp_request(
        candidate,
        method,
        uri,
        authorization=authorization,
        timeout=timeout,
    )


def _rtsp_authorization(
    auth_state: Mapping[str, Any],
    method: str,
    uri: str,
    username: str,
    password: str,
) -> str:
    """Build the cached RTSP Authorization header."""
    if challenge := auth_state.get("digest"):
        return build_digest_authorization(
            challenge,
            method,
            uri,
            username,
            password,
        )
    if auth_state.get("basic"):
        return BasicAuth(username, password).encode()
    return ""


def _rtsp_uri(candidate: LanCandidate, path_or_uri: str) -> str:
    """Build an absolute RTSP URI for one candidate."""
    if path_or_uri.lower().startswith("rtsp://"):
        return path_or_uri
    path = path_or_uri if path_or_uri.startswith("/") else f"/{path_or_uri}"
    host = f"[{candidate.host}]" if ":" in candidate.host else candidate.host
    return f"rtsp://{host}:{candidate.port}{path}"


async def _async_rtsp_request(
    candidate: LanCandidate,
    method: str,
    uri: str,
    *,
    authorization: str = "",
    timeout: float,
) -> RtspResponse:
    """Send one bounded RTSP control request over TCP."""
    writer: asyncio.StreamWriter | None = None
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(candidate.host, candidate.port)
            headers = [
                f"{method} {uri} RTSP/1.0",
                "CSeq: 1",
                "User-Agent: Home Assistant HiEasy",
            ]
            if method == "DESCRIBE":
                headers.append("Accept: application/sdp")
            if authorization:
                headers.append(f"Authorization: {authorization}")
            request = "\r\n".join((*headers, "", "")).encode("utf-8")
            writer.write(request)
            await writer.drain()
            head = await reader.readuntil(b"\r\n\r\n")
            status, response_headers = _parse_rtsp_head(head)
            content_length = _rtsp_content_length(response_headers)
            body = b""
            if content_length:
                body = await reader.readexactly(min(content_length, _MAX_RTSP_BODY))
            return RtspResponse(status, response_headers, body)
    except (
        OSError,
        TimeoutError,
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        ValueError,
    ) as err:
        raise LanError(str(err)) from err
    finally:
        if writer is not None:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()


def _parse_rtsp_head(payload: bytes) -> tuple[int, dict[str, str]]:
    """Parse an RTSP status line and response headers."""
    lines = payload.decode("iso-8859-1", "replace").split("\r\n")
    status_parts = lines[0].split(None, 2)
    if len(status_parts) < 2 or not status_parts[0].upper().startswith("RTSP/"):
        raise ValueError("Phản hồi không phải RTSP")
    status = int(status_parts[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, separator, value = line.partition(":")
        if separator:
            headers[name.strip().lower()] = value.strip()
    return status, headers


def _rtsp_content_length(headers: Mapping[str, str]) -> int:
    """Return a safe RTSP response body length."""
    try:
        return max(0, int(headers.get("content-length", "0")))
    except ValueError:
        return 0


async def _async_probe_onvif(
    session: ClientSession,
    device: CloudDevice,
    candidate: LanCandidate,
    service_url: str,
    *,
    timeout: float,
    max_channels: int,
) -> LanConnection | None:
    """Get an RTSP URI from a standard ONVIF media service."""
    service_parts = urlsplit(service_url)
    if not service_parts.hostname:
        return None
    service_client = LanHttpClient(
        session,
        f"{service_parts.scheme or candidate.scheme}://{service_parts.hostname}:{service_parts.port or candidate.port}",
        device.username,
        device.password,
        timeout=timeout,
    )
    service_path = service_parts.path or "/onvif/device_service"
    try:
        capabilities_xml = await _async_onvif_call(
            service_client,
            service_path,
            "GetCapabilities",
            "<tds:GetCapabilities xmlns:tds=\"http://www.onvif.org/ver10/device/wsdl\"><tds:Category>All</tds:Category></tds:GetCapabilities>",
            namespace="http://www.onvif.org/ver10/device/wsdl",
        )
    except LanError:
        capabilities_xml = ""
    media_url = parse_onvif_media_url(capabilities_xml) if capabilities_xml else None
    media_url = media_url or service_url
    media_parts = urlsplit(media_url)
    media_host = media_parts.hostname or candidate.host
    try:
        media_address = ipaddress.ip_address(media_host)
        if media_address.is_unspecified or media_address.is_loopback:
            media_host = candidate.host
    except ValueError:
        pass
    media_client = LanHttpClient(
        session,
        f"{media_parts.scheme or candidate.scheme}://{media_host}:{media_parts.port or candidate.port}",
        device.username,
        device.password,
        timeout=timeout,
    )
    media_path = media_parts.path or service_path
    profiles_xml = await _async_onvif_call(
        media_client,
        media_path,
        "GetProfiles",
        "<trt:GetProfiles/>",
    )
    profiles = parse_onvif_profiles(profiles_xml)
    if not profiles:
        return None
    connection = LanConnection(
        host=candidate.host,
        http_port=candidate.port,
        scheme=candidate.scheme,
        command_port=candidate.port,
        transport="onvif_rtsp",
        onvif_service_url=service_url,
        online=True,
    )
    cloud_channels = min(max(device.channel_count, 1), max_channels)
    profiles_per_channel = (
        min(3, len(profiles))
        if cloud_channels == 1
        else max(1, min(3, len(profiles) // cloud_channels))
    )
    for index, profile in enumerate(profiles[: cloud_channels * profiles_per_channel]):
        channel = min(index // profiles_per_channel + 1, cloud_channels)
        stream_index = index % profiles_per_channel + 1
        uri_xml = await _async_onvif_call(
            media_client,
            media_path,
            "GetStreamUri",
            f"""<trt:GetStreamUri>
 <trt:StreamSetup><tt:Stream xmlns:tt="http://www.onvif.org/ver10/schema">RTP-Unicast</tt:Stream>
 <tt:Transport xmlns:tt="http://www.onvif.org/ver10/schema"><tt:Protocol>RTSP</tt:Protocol></tt:Transport>
 </trt:StreamSetup><trt:ProfileToken>{profile}</trt:ProfileToken>
</trt:GetStreamUri>""",
        )
        uri = parse_onvif_stream_uri(uri_xml)
        if uri:
            connection.streams[(channel, stream_index)] = normalize_rtsp_uri(
                uri,
                connection.host,
                None,
                device.username,
                device.password,
            )
    return connection if connection.streams else None


async def _async_onvif_call(
    client: LanHttpClient,
    path: str,
    action: str,
    body: str,
    *,
    namespace: str = _ONVIF_NS,
) -> str:
    """Call one ONVIF SOAP operation."""
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="{_SOAP_ENV}" xmlns:trt="{_ONVIF_NS}">
 <s:Body>{body}</s:Body>
</s:Envelope>"""
    response = await client.async_request(
        "POST",
        path,
        body=envelope,
        headers={
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": f"{namespace}/{action}",
        },
    )
    return response.text


async def async_reboot(
    session: ClientSession,
    runtime: DeviceRuntime,
    *,
    timeout: float = 2.0,
) -> None:
    """Send the documented HiEasy reboot CGI command."""
    client = client_for_runtime(session, runtime, timeout=timeout)
    await client.async_request("PUT", "/System/Reboot", expected_status=(200, 202, 204))


def client_for_runtime(
    session: ClientSession,
    runtime: DeviceRuntime,
    *,
    timeout: float = DEFAULT_SCAN_TIMEOUT,
) -> LanHttpClient:
    """Create a local client for a discovered runtime."""
    if runtime.lan is None:
        raise LanError("Thiết bị chưa được phát hiện trong mạng LAN")
    if not runtime.lan.command_available:
        raise LanError("Camera chỉ có luồng RTSP, không có endpoint HTTP để gửi lệnh")
    port = runtime.lan.command_port or runtime.lan.http_port
    return LanHttpClient(
        session,
        f"{runtime.lan.scheme}://{runtime.lan.host}:{port}",
        runtime.cloud.username,
        runtime.cloud.password,
        timeout=timeout,
    )


async def async_set_enable(
    session: ClientSession,
    runtime: DeviceRuntime,
    path: str,
    enable: bool,
    *,
    aliases: Sequence[str] = ("Enable", "Enabled", "State"),
    root_name: str = "Config",
    fallback_field: str = "Enable",
    timeout: float = 3.0,
) -> None:
    """Read, mutate and write an enable-style XML setting."""
    client = client_for_runtime(session, runtime, timeout=timeout)
    old_xml = runtime.lan.xml.get(path, "") if runtime.lan else ""
    if not old_xml:
        old_xml = await client.async_get_xml(path)
    new_xml = mutate_first_alias(
        old_xml,
        aliases,
        enable,
        root_name=root_name,
        fallback_field=fallback_field,
    )
    await client.async_put_xml(path, new_xml)
    if runtime.lan is not None:
        cache_connection_xml(runtime.lan, path, new_xml)
        runtime.lan.online = True


async def async_set_xml_value(
    session: ClientSession,
    runtime: DeviceRuntime,
    path: str,
    value: str | float | bool,
    *,
    aliases: Sequence[str],
    root_name: str,
    fallback_field: str,
    timeout: float = 3.0,
) -> None:
    """Read, mutate and write an arbitrary scalar XML field."""
    client = client_for_runtime(session, runtime, timeout=timeout)
    old_xml = runtime.lan.xml.get(path, "") if runtime.lan else ""
    if not old_xml:
        old_xml = await client.async_get_xml(path)
    new_xml = mutate_first_alias(
        old_xml,
        aliases,
        value,
        root_name=root_name,
        fallback_field=fallback_field,
    )
    await client.async_put_xml(path, new_xml)
    if runtime.lan is not None:
        cache_connection_xml(runtime.lan, path, new_xml)
        runtime.lan.online = True


def cache_connection_xml(connection: LanConnection, path: str, xml_text: str) -> None:
    """Replace one XML endpoint and its flattened values atomically."""
    connection.xml[path] = xml_text
    prefix = f"{path}:".lower()
    for key in tuple(connection.values):
        if key.lower().startswith(prefix):
            connection.values.pop(key, None)
    connection.values.update(
        {f"{path}:{key}": value for key, value in flatten_xml(xml_text).items()}
    )


def _candidates_from_hints(
    hints: Iterable[str],
    http_ports: Iterable[int],
    rtsp_ports: Iterable[int],
) -> list[LanCandidate]:
    """Build likely local candidates from cloud-provided addresses."""
    return _candidates_for_hosts(
        hints,
        http_ports,
        rtsp_ports,
        source="cloud-hint",
    )


def _candidates_for_hosts(
    hosts: Iterable[str],
    http_ports: Iterable[int],
    rtsp_ports: Iterable[int],
    *,
    source: str,
) -> list[LanCandidate]:
    """Build HTTP/ONVIF and RTSP candidates for explicit hosts."""
    candidates: list[LanCandidate] = []
    web_ports = tuple(http_ports)
    media_ports = tuple(rtsp_ports)
    for host in hosts:
        normalized = host.strip().strip("[]")
        if not _is_valid_host(normalized):
            continue
        candidates.extend(
            LanCandidate("http", normalized, port, source) for port in web_ports
        )
        candidates.extend(
            LanCandidate("rtsp", normalized, port, source) for port in media_ports
        )
    return _dedupe_candidates(candidates)


def _is_valid_host(host: str) -> bool:
    if not host or "://" in host or any(char in host for char in "/@?#"):
        return False
    try:
        address = ipaddress.ip_address(host)
        return not (
            address.is_loopback
            or address.is_unspecified
            or address.is_multicast
        )
    except ValueError:
        return bool(_HOSTNAME_RE.fullmatch(host))


def _dedupe_candidates(candidates: Iterable[LanCandidate]) -> list[LanCandidate]:
    result: list[LanCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.key.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


async def _async_filter_open_candidates(
    candidates: Sequence[LanCandidate],
    *,
    timeout: float,
) -> list[LanCandidate]:
    """Drop closed ports before issuing authenticated protocol requests."""
    semaphore = asyncio.Semaphore(96)
    open_candidates: list[LanCandidate] = []

    async def check(candidate: LanCandidate) -> None:
        async with semaphore:
            writer: asyncio.StreamWriter | None = None
            try:
                async with asyncio.timeout(timeout):
                    _reader, writer = await asyncio.open_connection(candidate.host, candidate.port)
                open_candidates.append(candidate)
            except (OSError, TimeoutError):
                return
            finally:
                if writer is not None:
                    writer.close()
                    with suppress(OSError):
                        await writer.wait_closed()

    await asyncio.gather(*(check(candidate) for candidate in candidates))
    return _dedupe_candidates(open_candidates)


def _dedupe_networks(networks: Iterable[ipaddress.IPv4Network]) -> list[ipaddress.IPv4Network]:
    result: list[ipaddress.IPv4Network] = []
    seen: set[str] = set()
    for network in networks:
        key = str(network)
        if key not in seen:
            result.append(network)
            seen.add(key)
    return result
