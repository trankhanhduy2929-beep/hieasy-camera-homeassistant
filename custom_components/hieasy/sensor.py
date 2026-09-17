"""Diagnostic sensors for HiEasy cloud and LAN state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ENDPOINT_AIR_QUALITY,
    ENDPOINT_DISK,
    ENDPOINT_POWER_CONFIG,
    ENDPOINT_RUNNING_INFO,
    ENDPOINT_SIM_INFO,
    ENDPOINT_VOICE_LIGHT_STATE,
    ENDPOINT_WIFI_CONFIG,
    ENDPOINT_WIFI_WIRELESS_EX,
)
from .entity import HiEasyEntity, xml_value
from .models import DeviceRuntime


@dataclass(frozen=True, kw_only=True)
class HiEasySensorDescription(SensorEntityDescription):
    """Describe a HiEasy diagnostic sensor."""

    value_fn: Callable[[DeviceRuntime], StateType]
    enabled_default: bool = True


@dataclass(frozen=True, kw_only=True)
class HiEasyXmlSensorDescription(SensorEntityDescription):
    """Describe a sensor reading a local XML value."""

    path: str
    aliases: tuple[str, ...]
    enabled_default: bool = True


def _identity(runtime: DeviceRuntime, key: str, cloud_value: Any) -> Any:
    if runtime.lan and runtime.lan.identity.get(key):
        return runtime.lan.identity[key]
    return cloud_value


def _battery(runtime: DeviceRuntime) -> StateType:
    value = xml_value(
        runtime,
        ENDPOINT_RUNNING_INFO,
        "BatteryPower",
        "Battery",
        "Power",
    )
    return value if value is not None else runtime.cloud.battery


def _signal(runtime: DeviceRuntime) -> StateType:
    value = xml_value(
        runtime,
        ENDPOINT_RUNNING_INFO,
        "SignalIntensity",
        "SignalVal",
        "Signal",
        "WifiQuality",
    )
    return value if value is not None else runtime.cloud.signal


SENSORS: tuple[HiEasySensorDescription, ...] = (
    HiEasySensorDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: _identity(runtime, "model", runtime.cloud.model),
    ),
    HiEasySensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: _identity(runtime, "firmware", runtime.cloud.firmware),
    ),
    HiEasySensorDescription(
        key="serial",
        translation_key="serial",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: _identity(runtime, "serial", runtime.cloud.serial),
    ),
    HiEasySensorDescription(
        key="mac",
        translation_key="mac",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: _identity(runtime, "mac", runtime.cloud.mac),
    ),
    HiEasySensorDescription(
        key="device_type",
        translation_key="device_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.cloud.device_type or runtime.cloud.dtype,
    ),
    HiEasySensorDescription(
        key="cloud_status",
        translation_key="cloud_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.cloud.cloud_status,
    ),
    HiEasySensorDescription(
        key="channel_count",
        translation_key="channel_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.cloud.channel_count,
    ),
    HiEasySensorDescription(
        key="local_ip",
        translation_key="local_ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.lan.host if runtime.lan else None,
    ),
    HiEasySensorDescription(
        key="transport",
        translation_key="transport",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.lan.transport if runtime.lan else "cloud_only",
    ),
    HiEasySensorDescription(
        key="command_port",
        translation_key="command_port",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.lan.command_port if runtime.lan else None,
    ),
    HiEasySensorDescription(
        key="media_port",
        translation_key="media_port",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda runtime: runtime.lan.media_port if runtime.lan else None,
    ),
    HiEasySensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery,
    ),
    HiEasySensorDescription(
        key="signal",
        translation_key="signal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_signal,
    ),
    HiEasySensorDescription(
        key="iccid",
        translation_key="iccid",
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_default=False,
        value_fn=lambda runtime: runtime.cloud.iccid,
    ),
)

XML_SENSORS: tuple[HiEasyXmlSensorDescription, ...] = (
    HiEasyXmlSensorDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        path=ENDPOINT_WIFI_CONFIG,
        aliases=("SSID",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        path=ENDPOINT_WIFI_CONFIG,
        aliases=("SignalValue",),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="wifi_signal_strength",
        translation_key="wifi_signal_strength",
        path=ENDPOINT_WIFI_WIRELESS_EX,
        aliases=("WifiSignalStrength", "SignalStrength"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="wifi_name",
        translation_key="wifi_name",
        path=ENDPOINT_WIFI_WIRELESS_EX,
        aliases=("WifiName",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="sim_operator",
        translation_key="sim_operator",
        path=ENDPOINT_SIM_INFO,
        aliases=("Operator",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="sim_signal",
        translation_key="sim_signal",
        path=ENDPOINT_SIM_INFO,
        aliases=("SignalVal", "SignalStrength"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="power_status",
        translation_key="power_status",
        path=ENDPOINT_POWER_CONFIG,
        aliases=("PowerStatus",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="power_voltage",
        translation_key="power_voltage",
        path=ENDPOINT_POWER_CONFIG,
        aliases=("PowerVoltage",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="battery_percent_local",
        translation_key="battery_percent_local",
        path=ENDPOINT_POWER_CONFIG,
        aliases=("CurrentPowerPercentage",),
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="sdcard_total",
        translation_key="sdcard_total",
        path=ENDPOINT_DISK,
        aliases=("TotalCapacity",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="sdcard_free",
        translation_key="sdcard_free",
        path=ENDPOINT_DISK,
        aliases=("AvailableCapacity",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="sdcard_format_status",
        translation_key="sdcard_format_status",
        path=ENDPOINT_DISK,
        aliases=("DiskFormatStatus",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HiEasyXmlSensorDescription(
        key="voice_light_remaining",
        translation_key="voice_light_remaining",
        path=ENDPOINT_VOICE_LIGHT_STATE,
        aliases=("RemainTime",),
        native_unit_of_measurement="s",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="air_quality",
        translation_key="air_quality",
        path=ENDPOINT_AIR_QUALITY,
        aliases=("CurrentAirQualityLevel",),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HiEasyXmlSensorDescription(
        key="alarm_count_today",
        translation_key="alarm_count_today",
        path=ENDPOINT_RUNNING_INFO,
        aliases=("AlarmCount",),
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    HiEasyXmlSensorDescription(
        key="people_count_today",
        translation_key="people_count_today",
        path=ENDPOINT_RUNNING_INFO,
        aliases=("PeopleDetectCount",),
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    HiEasyXmlSensorDescription(
        key="awaken_duration",
        translation_key="awaken_duration",
        path=ENDPOINT_RUNNING_INFO,
        aliases=("AwakenDuration",),
        native_unit_of_measurement="s",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    HiEasyXmlSensorDescription(
        key="preview_duration",
        translation_key="preview_duration",
        path=ENDPOINT_RUNNING_INFO,
        aliases=("PreviewDuration",),
        native_unit_of_measurement="s",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy diagnostic sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for runtime in coordinator.devices.values():
        entities.extend(
            HiEasySensor(coordinator, runtime.cloud.did, description)
            for description in SENSORS
        )
        entities.extend(
            HiEasyXmlSensor(coordinator, runtime.cloud.did, description)
            for description in XML_SENSORS
        )
    async_add_entities(entities)


class HiEasySensor(HiEasyEntity, SensorEntity):
    """Represent one cloud or local diagnostic value."""

    entity_description: HiEasySensorDescription

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasySensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._attr_entity_registry_enabled_default = description.enabled_default

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        runtime = self.runtime
        return self.entity_description.value_fn(runtime) if runtime else None


class HiEasyXmlSensor(HiEasyEntity, SensorEntity):
    """Represent one local XML diagnostic value."""

    entity_description: HiEasyXmlSensorDescription

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasyXmlSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._attr_entity_registry_enabled_default = description.enabled_default

    @property
    def native_value(self) -> StateType:
        """Return the XML value."""
        return xml_value(
            self.runtime,
            self.entity_description.path,
            *self.entity_description.aliases,
        )

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
