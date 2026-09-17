"""Data models shared by the HiEasy integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class CloudDevice:
    """A device returned by the HiEasy account API."""

    did: str
    name: str
    username: str
    password: str
    mac: str | None = None
    serial: str | None = None
    model: str | None = None
    firmware: str | None = None
    device_type: str | None = None
    dtype: str | None = None
    channel_count: int = 1
    cloud_status: str | int | bool | None = None
    battery: float | None = None
    signal: float | None = None
    iccid: str | None = None
    imei: str | None = None
    local_hints: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def unique_id(self) -> str:
        """Return a stable device identifier."""
        return self.did.strip().lower()


@dataclass(slots=True)
class LanConnection:
    """Local CGI/ONVIF connection discovered for a cloud device."""

    host: str
    http_port: int | None
    scheme: str = "http"
    command_port: int | None = None
    media_port: int | None = None
    transport: str = "lan"
    streams: dict[tuple[int, int], str] = field(default_factory=dict)
    xml: dict[str, str] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    identity: dict[str, str] = field(default_factory=dict)
    supports_ptz: bool = False
    onvif_service_url: str | None = None
    online: bool = False
    last_error: str | None = None

    def stream_uri(self, channel: int, stream: int) -> str | None:
        """Return a discovered stream URI."""
        return self.streams.get((channel, stream))

    @property
    def command_available(self) -> bool:
        """Return whether the connection can carry proprietary HTTP commands."""
        return (
            self.online
            and self.scheme in {"http", "https"}
            and (self.command_port is not None or self.http_port is not None)
        )


@dataclass(slots=True)
class DeviceRuntime:
    """Combined cloud and local state for one HiEasy device."""

    cloud: CloudDevice
    lan: LanConnection | None = None
    last_cloud_refresh: datetime | None = None

    @property
    def online(self) -> bool:
        """Return whether local or cloud data indicates that the device is online."""
        if self.lan is not None and self.lan.online:
            return True
        value = self.cloud.cloud_status
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value == 1
        if isinstance(value, str):
            return value.strip().lower() in {
                "1",
                "online",
                "connected",
                "true",
                "normal",
            }
        return False
