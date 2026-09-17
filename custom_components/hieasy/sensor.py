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

from .const import ENDPOINT_RUNNING_INFO
from .entity import HiEasyEntity, xml_value
from .models import DeviceRuntime


@dataclass(frozen=True, kw_only=True)
class HiEasySensorDescription(SensorEntityDescription):
    """Describe a HiEasy diagnostic sensor."""

    value_fn: Callable[[DeviceRuntime], StateType]
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


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy diagnostic sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        HiEasySensor(coordinator, runtime.cloud.did, description)
        for runtime in coordinator.devices.values()
        for description in SENSORS
    )


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
