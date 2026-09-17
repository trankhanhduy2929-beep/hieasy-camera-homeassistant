"""Coordinator combining HiEasy cloud and local device state."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client, update_coordinator
from homeassistant.util import dt as dt_util

from .api import (
    HiEasyApiError,
    HiEasyCannotConnectError,
    HiEasyCloudClient,
    HiEasyInvalidAuthError,
)
from .const import (
    CONF_ACCOUNT,
    CONF_DISCOVER_LAN,
    CONF_LAN_HOSTS,
    CONF_LAN_NETWORKS,
    CONF_MAX_SCAN_HOSTS,
    CONF_REGION,
    CONF_RTSP_PATHS,
    CONF_RTSP_PORTS,
    CONF_SCAN_PORTS,
    CONF_SCAN_TIMEOUT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_CLOUD_REFRESH,
    DEFAULT_DISCOVER_LAN,
    DEFAULT_MAX_SCAN_HOSTS,
    DEFAULT_RTSP_PATHS,
    DEFAULT_RTSP_PORTS,
    DEFAULT_SCAN_PORTS,
    DEFAULT_SCAN_TIMEOUT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    REGION_AUTO,
)
from .lan import (
    LanCandidate,
    LanError,
    async_discover_devices,
    async_probe_candidate,
    async_reboot,
    async_set_enable,
    async_set_xml_value,
    cache_connection_xml,
    client_for_runtime,
)
from .models import DeviceRuntime, LanConnection

_LOGGER = logging.getLogger(__name__)


class HiEasyCoordinator(
    update_coordinator.DataUpdateCoordinator[dict[str, DeviceRuntime]]
):
    """Keep account discovery and local camera state synchronized."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.session = session or aiohttp_client.async_get_clientsession(hass)
        self.cloud = HiEasyCloudClient(
            self.session,
            str(entry.data[CONF_ACCOUNT]),
            str(entry.data[CONF_PASSWORD]),
            str(entry.data.get(CONF_REGION, REGION_AUTO)),
        )
        self.devices: dict[str, DeviceRuntime] = {}
        self._last_cloud_refresh = None
        self._last_discovery = None
        self._force_discovery = True

        interval = int(self.option(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        interval = max(MIN_UPDATE_INTERVAL, min(interval, MAX_UPDATE_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    def option(self, key: str, default: Any) -> Any:
        """Return an option with config-entry data fallback."""
        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _set_lan_connection(
        self,
        runtime: DeviceRuntime,
        connection: LanConnection,
    ) -> None:
        """Store refreshed LAN data."""
        runtime.lan = connection

    async def _async_update_data(self) -> dict[str, DeviceRuntime]:
        """Refresh cloud metadata and local endpoints."""
        now = dt_util.utcnow()
        cloud_due = (
            not self.devices
            or self._last_cloud_refresh is None
            or now - self._last_cloud_refresh >= DEFAULT_CLOUD_REFRESH
        )
        if cloud_due:
            await self._async_refresh_cloud(now)

        if not self.devices:
            return {}

        discovery_due = (
            self._force_discovery
            or self._last_discovery is None
            or now - self._last_discovery >= timedelta(minutes=5)
        )
        if discovery_due:
            await self._async_discover_missing(now, include_existing=self._force_discovery)
        else:
            await self._async_refresh_existing()

        self._force_discovery = False
        return dict(self.devices)

    async def _async_refresh_cloud(self, now) -> None:
        """Refresh devices while retaining useful LAN state on transient errors."""
        try:
            cloud_devices = await self.cloud.async_get_devices()
        except HiEasyInvalidAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (HiEasyCannotConnectError, HiEasyApiError) as err:
            if not self.devices:
                raise update_coordinator.UpdateFailed(str(err)) from err
            _LOGGER.warning("Không làm mới được cloud HiEasy, giữ dữ liệu cũ: %s", err)
            return

        updated: dict[str, DeviceRuntime] = {}
        for cloud_device in cloud_devices:
            existing = self.devices.get(cloud_device.unique_id)
            updated[cloud_device.unique_id] = DeviceRuntime(
                cloud=cloud_device,
                lan=existing.lan if existing else None,
                last_cloud_refresh=now,
            )
        self.devices = updated
        self._last_cloud_refresh = now

    async def _async_discover_missing(self, now, *, include_existing: bool) -> None:
        """Run WS-Discovery/cloud hints and a bounded subnet scan."""
        targets = [
            runtime.cloud
            for runtime in self.devices.values()
            if include_existing or runtime.lan is None
        ]
        if not targets:
            await self._async_refresh_existing()
            self._last_discovery = now
            return
        try:
            found = await async_discover_devices(
                self.session,
                targets,
                discover_lan=bool(
                    self.option(CONF_DISCOVER_LAN, DEFAULT_DISCOVER_LAN)
                ),
                hosts=self.option(CONF_LAN_HOSTS, ""),
                networks=self.option(CONF_LAN_NETWORKS, ""),
                scan_ports=self.option(CONF_SCAN_PORTS, DEFAULT_SCAN_PORTS),
                rtsp_ports=self.option(CONF_RTSP_PORTS, DEFAULT_RTSP_PORTS),
                rtsp_paths=self.option(CONF_RTSP_PATHS, DEFAULT_RTSP_PATHS),
                scan_timeout=float(
                    self.option(CONF_SCAN_TIMEOUT, DEFAULT_SCAN_TIMEOUT)
                ),
                max_scan_hosts=int(
                    self.option(CONF_MAX_SCAN_HOSTS, DEFAULT_MAX_SCAN_HOSTS)
                ),
            )
        except (LanError, OSError, RuntimeError, ValueError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Dò LAN HiEasy thất bại: %s", err)
            found = {}

        for unique_id, connection in found.items():
            if runtime := self.devices.get(unique_id):
                self._set_lan_connection(runtime, connection)
        if include_existing:
            for unique_id, runtime in self.devices.items():
                if unique_id not in found and runtime.lan is not None:
                    runtime.lan.online = False
                    runtime.lan.last_error = "Không tìm thấy thiết bị trong lần dò mới"
        self._last_discovery = now

    async def _async_refresh_existing(self) -> None:
        """Refresh already paired cameras without scanning the subnet."""
        timeout = max(
            float(self.option(CONF_SCAN_TIMEOUT, DEFAULT_SCAN_TIMEOUT)),
            1.5,
        )

        async def refresh(runtime: DeviceRuntime) -> None:
            if runtime.lan is None:
                return
            port = (
                runtime.lan.media_port
                if runtime.lan.scheme == "rtsp"
                else runtime.lan.http_port
            )
            if port is None:
                runtime.lan.online = False
                runtime.lan.last_error = "Thiếu cổng kết nối cục bộ"
                return
            candidate = LanCandidate(
                runtime.lan.scheme,
                runtime.lan.host,
                port,
                "existing",
                runtime.lan.onvif_service_url,
            )
            try:
                connection = await async_probe_candidate(
                    self.session,
                    runtime.cloud,
                    candidate,
                    timeout=timeout,
                    max_channels=8,
                    rtsp_paths=self.option(CONF_RTSP_PATHS, DEFAULT_RTSP_PATHS),
                )
            except (LanError, OSError) as err:
                runtime.lan.online = False
                runtime.lan.last_error = str(err)
                return
            if connection is None:
                runtime.lan.online = False
                runtime.lan.last_error = "Thiết bị không phản hồi"
                return
            self._set_lan_connection(runtime, connection)

        await asyncio.gather(*(refresh(runtime) for runtime in self.devices.values()))

    def runtime_for_did(self, did: str) -> DeviceRuntime:
        """Return a runtime by DID, case-insensitively."""
        key = did.strip().lower()
        runtime = self.devices.get(key)
        if runtime is not None:
            return runtime
        for candidate in self.devices.values():
            if candidate.cloud.did.lower() == key:
                return candidate
        raise LanError(f"Không tìm thấy DID {did}")

    async def async_force_rediscovery(self) -> None:
        """Force cloud/LAN rediscovery on the next refresh."""
        self._force_discovery = True
        self._last_cloud_refresh = None
        await self.async_request_refresh()

    async def async_send_command(
        self,
        did: str,
        path: str,
        method: str = "GET",
        body: str | None = None,
    ) -> str:
        """Send an advanced local CGI command and return its response body."""
        if not path.startswith("/") or "://" in path:
            raise LanError("Đường dẫn lệnh phải bắt đầu bằng / và không được chứa URL")
        runtime = self.runtime_for_did(did)
        client = client_for_runtime(self.session, runtime, timeout=5.0)
        command = method.upper()
        if command not in {"GET", "PUT", "POST"}:
            raise LanError("Chỉ hỗ trợ GET, PUT hoặc POST")
        headers: dict[str, str] = {}
        if body:
            headers["Content-Type"] = (
                "text/xml; charset=UTF-8"
                if body.lstrip().startswith("<")
                else "text/plain; charset=UTF-8"
            )
        response = await client.async_request(
            command,
            path,
            body=body,
            headers=headers,
            expected_status=(200, 201, 202, 204),
        )
        if runtime.lan is not None and response.text.lstrip().startswith("<"):
            cache_connection_xml(runtime.lan, path, response.text)
            runtime.lan.online = True
        return response.text

    async def async_set_enabled(
        self,
        did: str,
        path: str,
        enabled: bool,
        *,
        aliases: Sequence[str],
        root_name: str,
        fallback_field: str = "Enable",
    ) -> None:
        """Set one enable-like device configuration."""
        runtime = self.runtime_for_did(did)
        await async_set_enable(
            self.session,
            runtime,
            path,
            enabled,
            aliases=aliases,
            root_name=root_name,
            fallback_field=fallback_field,
        )
        self.async_set_updated_data(dict(self.devices))

    async def async_reboot_device(self, did: str) -> None:
        """Reboot a locally connected device."""
        await async_reboot(self.session, self.runtime_for_did(did))

    async def async_set_value(
        self,
        did: str,
        path: str,
        value: str | float | bool,
        *,
        aliases: Sequence[str],
        root_name: str,
        fallback_field: str,
    ) -> None:
        """Set one scalar XML configuration value."""
        runtime = self.runtime_for_did(did)
        await async_set_xml_value(
            self.session,
            runtime,
            path,
            value,
            aliases=aliases,
            root_name=root_name,
            fallback_field=fallback_field,
        )
        self.async_set_updated_data(dict(self.devices))

    async def async_goto_preset(self, did: str, channel: int, preset: int) -> None:
        """Move a PTZ camera to a preset using the APK's Param1 payload."""
        if channel < 1 or preset < 0:
            raise LanError("Kênh phải >= 1 và preset phải >= 0")
        await self.async_send_command(
            did,
            f"/PTZ/{channel}/Presets/Goto",
            "PUT",
            f"Param1={preset}",
        )

    def diagnostic_data(self) -> dict[str, Any]:
        """Return non-secret coordinator metadata for diagnostics."""
        return {
            "requested_region": self.cloud.requested_region,
            "active_region": self.cloud.region,
            "device_count": len(self.devices),
            "last_cloud_refresh": self._last_cloud_refresh,
            "last_discovery": self._last_discovery,
        }
