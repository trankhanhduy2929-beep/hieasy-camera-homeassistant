"""Select entities for HiEasy XML settings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ENDPOINT_ATMOSPHERE_LIGHT,
    ENDPOINT_IMAGE_BASIC,
    ENDPOINT_INTERCOM_MODE,
    ENDPOINT_IRCUT,
    ENDPOINT_IRCUT_EX,
    ENDPOINT_LIGHT_CONTROL,
    ENDPOINT_NIGHT_VISION,
    ENDPOINT_POWER_MANAGE,
    ENDPOINT_PTZ_CONFIG,
    ENDPOINT_RECORD_SCHEDULE,
)
from .entity import HiEasyLocalEntity, xml_value

_COMMON_NIGHT_MODES = (
    "Auto",
    "Day",
    "Night",
    "Color",
    "BlackWhite",
    "Smart",
    "0",
    "1",
    "2",
    "3",
)


@dataclass(frozen=True, kw_only=True)
class HiEasySelectDescription:
    """Describe one enum-like XML setting."""

    key: str
    translation_key: str
    path: str
    aliases: Sequence[str]
    root_name: str
    fallback_field: str
    options: Sequence[str] = ()
    channel: int | None = None


DEVICE_SELECTS: tuple[HiEasySelectDescription, ...] = (
    HiEasySelectDescription(
        key="night_vision_mode",
        translation_key="night_vision_mode",
        path=ENDPOINT_NIGHT_VISION,
        aliases=("NightVisionMode", "Mode"),
        root_name="DeviceNightVisionCfg",
        fallback_field="NightVisionMode",
        options=_COMMON_NIGHT_MODES,
    ),
    HiEasySelectDescription(
        key="intercom_mode",
        translation_key="intercom_mode",
        path=ENDPOINT_INTERCOM_MODE,
        aliases=("IntercomMode",),
        root_name="DeviceIntercomMode",
        fallback_field="IntercomMode",
        options=("HalfDuplex", "FullDuplex", "0", "1", "2"),
    ),
    HiEasySelectDescription(
        key="power_mode",
        translation_key="power_mode",
        path=ENDPOINT_POWER_MANAGE,
        aliases=("WorkMode", "DeviceWorkMode"),
        root_name="DevicePowerManageCfg",
        fallback_field="WorkMode",
        options=("0", "1", "2", "3"),
    ),
    HiEasySelectDescription(
        key="atmosphere_light_mode",
        translation_key="atmosphere_light_mode",
        path=ENDPOINT_ATMOSPHERE_LIGHT,
        aliases=("ModeType",),
        root_name="AtmosphereLightCfg",
        fallback_field="ModeType",
        options=("0", "1", "2", "3"),
    ),
    HiEasySelectDescription(
        key="light_mode",
        translation_key="light_mode",
        path=ENDPOINT_LIGHT_CONTROL,
        aliases=("IntellectOnLightEnable", "TimeOnLightEnable"),
        root_name="LightControlCfg",
        fallback_field="IntellectOnLightEnable",
        options=("0", "1"),
    ),
)

CHANNEL_SELECTS: tuple[HiEasySelectDescription, ...] = (
    HiEasySelectDescription(
        key="ircut_mode",
        translation_key="ircut_mode",
        path=ENDPOINT_IRCUT,
        aliases=("Mode", "ImageMode"),
        root_name="IrCutFillter",
        fallback_field="Mode",
        options=("0", "1", "2", "3", "Auto", "Day", "Night"),
    ),
    HiEasySelectDescription(
        key="ircut_scene",
        translation_key="ircut_scene",
        path=ENDPOINT_IRCUT_EX,
        aliases=("SceneMode",),
        root_name="IRCUTEX",
        fallback_field="SceneMode",
        options=("0", "1", "2", "3"),
    ),
    HiEasySelectDescription(
        key="flip_mode",
        translation_key="flip_mode",
        path=ENDPOINT_IMAGE_BASIC,
        aliases=("FlipMode",),
        root_name="Basic",
        fallback_field="FlipMode",
        options=("0", "1", "2", "3", "Normal", "Flip", "Mirror", "Rotate180"),
    ),
    HiEasySelectDescription(
        key="ptz_protocol",
        translation_key="ptz_protocol",
        path=ENDPOINT_PTZ_CONFIG,
        aliases=("Protocol",),
        root_name="PTZConfigChannel",
        fallback_field="Protocol",
        options=("PELCO_D", "PELCO_P", "0", "1", "2"),
    ),
    HiEasySelectDescription(
        key="ptz_watch_mode",
        translation_key="ptz_watch_mode",
        path=ENDPOINT_PTZ_CONFIG,
        aliases=("PTZWatch.WatchMode", "WatchMode"),
        root_name="PTZConfigChannel",
        fallback_field="WatchMode",
        options=("0", "1", "2"),
    ),
    HiEasySelectDescription(
        key="record_type",
        translation_key="record_type",
        path=ENDPOINT_RECORD_SCHEDULE,
        aliases=("RecordType",),
        root_name="RecordScheduleV2",
        fallback_field="RecordType",
        options=("0", "1", "2", "3"),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy select entities."""
    coordinator = entry.runtime_data
    entities: list[HiEasySelect] = []
    for runtime in coordinator.devices.values():
        did = runtime.cloud.did
        entities.extend(
            HiEasySelect(coordinator, did, description)
            for description in DEVICE_SELECTS
        )
        for channel in range(1, min(runtime.cloud.channel_count, 8) + 1):
            for template in CHANNEL_SELECTS:
                description = HiEasySelectDescription(
                    key=f"{template.key}_{channel}",
                    translation_key=template.translation_key,
                    path=template.path.format(channel=channel),
                    aliases=template.aliases,
                    root_name=template.root_name,
                    fallback_field=template.fallback_field,
                    options=template.options,
                    channel=channel,
                )
                entities.append(HiEasySelect(coordinator, did, description))
    async_add_entities(entities)


class HiEasySelect(HiEasyLocalEntity, SelectEntity):
    """Select one enum-like XML value accepted by the camera."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: HiEasySelectDescription

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasySelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        if description.channel is not None:
            self._attr_translation_placeholders = {"channel": str(description.channel)}

    @property
    def current_option(self) -> str | None:
        """Return the current raw mode."""
        value = xml_value(
            self.runtime,
            self.entity_description.path,
            *self.entity_description.aliases,
        )
        return str(value) if value is not None else None

    @property
    def options(self) -> list[str]:
        """Return common modes plus the device's current vendor-specific value."""
        values = [str(option) for option in self.entity_description.options]
        current = self.current_option
        if current and current not in values:
            values.insert(0, current)
        return values

    @property
    def available(self) -> bool:
        """Require the endpoint to have answered."""
        runtime = self.runtime
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and runtime.lan.command_available
            and self.entity_description.path in runtime.lan.xml
        )

    async def async_select_option(self, option: str) -> None:
        """Write the selected value while preserving the rest of the XML."""
        await self.coordinator.async_set_value(
            self.did,
            self.entity_description.path,
            option,
            aliases=self.entity_description.aliases,
            root_name=self.entity_description.root_name,
            fallback_field=self.entity_description.fallback_field,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the backing CGI path."""
        return {"cgi_path": self.entity_description.path}
