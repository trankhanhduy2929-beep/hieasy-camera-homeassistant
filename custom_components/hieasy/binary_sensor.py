"""Binary sensors for HiEasy connectivity and configuration state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import HiEasyEntity, xml_value
from .models import DeviceRuntime
from .protocol import parse_bool


@dataclass(frozen=True, kw_only=True)
class HiEasyBinaryDescription(BinarySensorEntityDescription):
    """Describe a HiEasy binary sensor."""

    value_fn: Callable[[DeviceRuntime], bool | None]
    local_required: bool = False


BASE_BINARY_SENSORS: tuple[HiEasyBinaryDescription, ...] = (
    HiEasyBinaryDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda runtime: runtime.online,
    ),
    HiEasyBinaryDescription(
        key="local_connection",
        translation_key="local_connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: bool(runtime.lan and runtime.lan.online),
    ),
    HiEasyBinaryDescription(
        key="ptz_supported",
        translation_key="ptz_supported",
        entity_category=EntityCategory.DIAGNOSTIC,
        local_required=True,
        value_fn=lambda runtime: runtime.lan.supports_ptz if runtime.lan else None,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy binary sensors."""
    coordinator = entry.runtime_data
    entities: list[HiEasyBinarySensor] = []
    for runtime in coordinator.devices.values():
        entities.extend(
            HiEasyBinarySensor(coordinator, runtime.cloud.did, description)
            for description in BASE_BINARY_SENSORS
        )
        entities.extend(
            HiEasyMotionEnabledSensor(
                coordinator,
                runtime.cloud.did,
                channel,
            )
            for channel in range(1, min(runtime.cloud.channel_count, 8) + 1)
        )
    async_add_entities(entities)


class HiEasyBinarySensor(HiEasyEntity, BinarySensorEntity):
    """Represent a HiEasy binary value."""

    entity_description: HiEasyBinaryDescription

    def __init__(self, coordinator, did: str, description: HiEasyBinaryDescription) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the binary state."""
        runtime = self.runtime
        return self.entity_description.value_fn(runtime) if runtime else None

    @property
    def available(self) -> bool:
        """Require LAN only for local-only capabilities."""
        runtime = self.runtime
        return (
            super().available
            and (
                not self.entity_description.local_required
                or bool(runtime and runtime.lan and runtime.lan.online)
            )
        )


class HiEasyMotionEnabledSensor(HiEasyEntity, BinarySensorEntity):
    """Expose whether motion processing is enabled for one channel."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "motion_enabled"

    def __init__(self, coordinator, did: str, channel: int) -> None:
        super().__init__(coordinator, did, f"motion_enabled_{channel}")
        self.channel = channel
        self._attr_translation_placeholders = {"channel": str(channel)}

    @property
    def is_on(self) -> bool | None:
        """Return the motion-enable setting."""
        value = xml_value(
            self.runtime,
            f"/Pictures/{self.channel}/MoveTrack",
            "Enable",
            "Enabled",
        )
        return parse_bool(value)

    @property
    def available(self) -> bool:
        """Require the setting endpoint to have answered."""
        runtime = self.runtime
        path = f"/Pictures/{self.channel}/MoveTrack"
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and runtime.lan.online
            and path in runtime.lan.xml
        )

