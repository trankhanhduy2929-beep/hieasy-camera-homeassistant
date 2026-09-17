"""Camera entities backed by local HiEasy RTSP or ONVIF streams."""

from __future__ import annotations

from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STREAM_MAIN, STREAM_NAMES, STREAM_SUB, STREAM_THIRD
from .entity import HiEasyLocalEntity


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up all advertised channels and stream profiles."""
    coordinator = entry.runtime_data
    entities = [
        HiEasyCamera(coordinator, runtime.cloud.did, channel, stream)
        for runtime in coordinator.devices.values()
        for channel in range(1, min(runtime.cloud.channel_count, 8) + 1)
        for stream in (STREAM_MAIN, STREAM_SUB, STREAM_THIRD)
    ]
    async_add_entities(entities)


class HiEasyCamera(HiEasyLocalEntity, Camera):
    """Represent one HiEasy channel/profile as an HA camera."""

    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_brand = "HiEasy"

    def __init__(self, coordinator, did: str, channel: int, stream: int) -> None:
        """Initialize a camera entity."""
        self.channel = channel
        self.stream_index = stream
        super().__init__(coordinator, did, f"camera_{channel}_{stream}")
        Camera.__init__(self)
        self._attr_translation_key = "stream"
        self._attr_translation_placeholders = {
            "channel": str(channel),
            "profile": STREAM_NAMES.get(stream, str(stream)),
        }

    @property
    def use_stream_for_stills(self) -> bool:
        """Use the RTSP stream for still images when HA requests one."""
        return True

    @property
    def available(self) -> bool:
        """Require a currently discovered stream URI."""
        runtime = self.runtime
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and runtime.lan.online
            and runtime.lan.stream_uri(self.channel, self.stream_index) is not None
        )

    async def stream_source(self) -> str | None:
        """Return the discovered RTSP/ONVIF stream URI."""
        runtime = self.runtime
        if runtime is None or runtime.lan is None:
            return None
        uri = runtime.lan.stream_uri(self.channel, self.stream_index)
        if uri is None:
            await self.coordinator.async_request_refresh()
            runtime = self.runtime
            uri = runtime.lan.stream_uri(self.channel, self.stream_index) if runtime and runtime.lan else None
        return uri

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose transport diagnostics without embedding the password."""
        runtime = self.runtime
        if runtime is None or runtime.lan is None:
            return {"channel": self.channel, "profile": STREAM_NAMES.get(self.stream_index)}
        lan = runtime.lan
        return {
            "channel": self.channel,
            "profile": STREAM_NAMES.get(self.stream_index, str(self.stream_index)),
            "transport": lan.transport,
            "local_ip": lan.host,
            "command_port": lan.command_port,
            "media_port": lan.media_port,
            "stream_available": lan.stream_uri(self.channel, self.stream_index) is not None,
        }
