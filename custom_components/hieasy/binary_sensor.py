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

from .const import (
    ENDPOINT_ALARM_OUT_STATE,
    ENDPOINT_CLOUD_STORAGE_STATUS,
    ENDPOINT_DISK,
    ENDPOINT_POWER_CONFIG,
    ENDPOINT_SIM_INFO,
    ENDPOINT_SLEEP_INFO,
    ENDPOINT_VOICE_LIGHT_STATE,
)
from .entity import HiEasyEntity, xml_value
from .models import DeviceRuntime
from .protocol import parse_bool


@dataclass(frozen=True, kw_only=True)
class HiEasyXmlBinaryDescription(BinarySensorEntityDescription):
    """Describe a read-only XML binary state."""

    path: str
    aliases: tuple[str, ...]
    channel: int | None = None


XML_BINARY_SENSORS: tuple[HiEasyXmlBinaryDescription, ...] = (
    HiEasyXmlBinaryDescription(
        key="sleeping",
        translation_key="sleeping",
        path=ENDPOINT_SLEEP_INFO,
        aliases=("SleepStatus",),
    ),
    HiEasyXmlBinaryDescription(
        key="alarm_out_state",
        translation_key="alarm_out_state",
        path=ENDPOINT_ALARM_OUT_STATE,
        aliases=("State",),
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    HiEasyXmlBinaryDescription(
        key="voice_light_active",
        translation_key="voice_light_active",
        path=ENDPOINT_VOICE_LIGHT_STATE,
        aliases=("State",),
        device_class=BinarySensorDeviceClass.SOUND,
    ),
    HiEasyXmlBinaryDescription(
        key="sdcard_present",
        translation_key="sdcard_present",
        path=ENDPOINT_DISK,
        aliases=("DiskStorageType", "TotalCapacity"),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    HiEasyXmlBinaryDescription(
        key="sim_present",
        translation_key="sim_present",
        path=ENDPOINT_SIM_INFO,
        aliases=("IsInUse", "ICCID"),
    ),
    HiEasyXmlBinaryDescription(
        key="low_battery",
        translation_key="low_battery",
        path=ENDPOINT_POWER_CONFIG,
        aliases=("LowBatteryAlarmSwitch",),
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    HiEasyXmlBinaryDescription(
        key="cloud_recording",
        translation_key="cloud_recording",
        path=ENDPOINT_CLOUD_STORAGE_STATUS,
        aliases=("EnableStatus", "Enable"),
    ),
)


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
        entities.extend(
            HiEasyXmlBinarySensor(
                coordinator,
                runtime.cloud.did,
                description,
            )
            for description in XML_BINARY_SENSORS
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


class HiEasyXmlBinarySensor(HiEasyEntity, BinarySensorEntity):
    """Represent a read-only binary state read from device XML."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    entity_description: HiEasyXmlBinaryDescription

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasyXmlBinaryDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, did, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the parsed state."""
        value = xml_value(
            self.runtime,
            self.entity_description.path,
            *self.entity_description.aliases,
        )
        if value is None:
            return None
        if self.entity_description.key == "sdcard_present":
            try:
                return float(str(value)) > 0
            except (TypeError, ValueError):
                return parse_bool(value)
        return parse_bool(value)

    @property
    def available(self) -> bool:
        """Require the endpoint to have answered."""
        runtime = self.runtime
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and runtime.lan.online
            and self.entity_description.path in runtime.lan.xml
        )

