"""Numeric HiEasy XML settings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ENDPOINT_ATMOSPHERE_LIGHT,
    ENDPOINT_AUDIO_STREAM,
    ENDPOINT_DND,
    ENDPOINT_IMAGE_BASIC,
    ENDPOINT_IRCUT,
    ENDPOINT_LIGHT_CONTROL,
    ENDPOINT_LIGHT_WARNING,
    ENDPOINT_MOTION,
    ENDPOINT_NIGHT_LED,
    ENDPOINT_NIGHT_VISION,
    ENDPOINT_ONE_CLICK_ALARM_CFG,
    ENDPOINT_PEOPLE_DETECT,
    ENDPOINT_PIR,
    ENDPOINT_POWER_CONFIG,
    ENDPOINT_PUSH_INTERVAL,
    ENDPOINT_RADAR,
    ENDPOINT_VOICE_LIGHT_CONFIG,
)
from .entity import HiEasyLocalEntity, xml_value


@dataclass(frozen=True, kw_only=True)
class HiEasyNumberDescription(NumberEntityDescription):
    """Describe one numeric XML setting."""

    path: str
    aliases: Sequence[str]
    root_name: str
    fallback_field: str
    channel: int | None = None


def _to_number(value: Any) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


DEVICE_NUMBERS: tuple[HiEasyNumberDescription, ...] = (
    HiEasyNumberDescription(
        key="dnd_duration",
        translation_key="dnd_duration",
        path=ENDPOINT_DND,
        aliases=("Duration",),
        root_name="DoNotDisturbMode",
        fallback_field="Duration",
        native_min_value=0,
        native_max_value=86400,
        native_step=60,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="night_led_duration",
        translation_key="night_led_duration",
        path=ENDPOINT_NIGHT_LED,
        aliases=("Duration",),
        root_name="NightLedInfo",
        fallback_field="Duration",
        native_min_value=0,
        native_max_value=3600,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="atmosphere_light_mode",
        translation_key="atmosphere_light_mode",
        path=ENDPOINT_ATMOSPHERE_LIGHT,
        aliases=("ModeType",),
        root_name="AtmosphereLightCfg",
        fallback_field="ModeType",
        native_min_value=0,
        native_max_value=255,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="alarm_volume",
        translation_key="alarm_volume",
        path=ENDPOINT_AUDIO_STREAM,
        aliases=("AlarmVolume", "AudioOutVolume"),
        root_name="AudioStream",
        fallback_field="AlarmVolume",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="mic_volume",
        translation_key="mic_volume",
        path=ENDPOINT_AUDIO_STREAM,
        aliases=("AudioInVolume",),
        root_name="AudioStream",
        fallback_field="AudioInVolume",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="speaker_volume",
        translation_key="speaker_volume",
        path=ENDPOINT_AUDIO_STREAM,
        aliases=("AudioOutVolume",),
        root_name="AudioStream",
        fallback_field="AudioOutVolume",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="fill_light_brightness",
        translation_key="fill_light_brightness",
        path=ENDPOINT_NIGHT_VISION,
        aliases=("FillLightBrightness",),
        root_name="DeviceNightVisionCfg",
        fallback_field="FillLightBrightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="low_battery_percent",
        translation_key="low_battery_percent",
        path=ENDPOINT_POWER_CONFIG,
        aliases=("SetPowerSavingPercentage",),
        root_name="PowerConfig",
        fallback_field="SetPowerSavingPercentage",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="light_brightness_person",
        translation_key="light_brightness_person",
        path=ENDPOINT_LIGHT_CONTROL,
        aliases=("HasPersonLightBright",),
        root_name="LightControlCfg",
        fallback_field="HasPersonLightBright",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="light_brightness_idle",
        translation_key="light_brightness_idle",
        path=ENDPOINT_LIGHT_CONTROL,
        aliases=("NoPersonLightBright",),
        root_name="LightControlCfg",
        fallback_field="NoPersonLightBright",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
)

CHANNEL_NUMBERS: tuple[HiEasyNumberDescription, ...] = (
    HiEasyNumberDescription(
        key="motion_sensitivity",
        translation_key="motion_sensitivity",
        path=ENDPOINT_MOTION,
        aliases=("Senstive", "Sensitivity"),
        root_name="Motion",
        fallback_field="Senstive",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="people_sensitivity",
        translation_key="people_sensitivity",
        path=ENDPOINT_PEOPLE_DETECT,
        aliases=("Senstive", "SenstiveV1", "Sensitivity"),
        root_name="PeopleDetect",
        fallback_field="Senstive",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="pir_sensitivity",
        translation_key="pir_sensitivity",
        path=ENDPOINT_PIR,
        aliases=("Senstive", "Sensitivity"),
        root_name="PirDetect",
        fallback_field="Senstive",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="radar_sensitivity",
        translation_key="radar_sensitivity",
        path=ENDPOINT_RADAR,
        aliases=("Senstive", "Sensitivity"),
        root_name="RadarDetect",
        fallback_field="Senstive",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="light_warning_delay",
        translation_key="light_warning_delay",
        path=ENDPOINT_LIGHT_WARNING,
        aliases=("DelayTime",),
        root_name="LightWarning",
        fallback_field="DelayTime",
        native_min_value=0,
        native_max_value=600,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="voice_light_alarm_time",
        translation_key="voice_light_alarm_time",
        path=ENDPOINT_VOICE_LIGHT_CONFIG,
        aliases=("AlarmTime", "Delay"),
        root_name="AlarmVoiceLightConfig",
        fallback_field="AlarmTime",
        native_min_value=0,
        native_max_value=600,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="one_click_alarm_time",
        translation_key="one_click_alarm_time",
        path=ENDPOINT_ONE_CLICK_ALARM_CFG,
        aliases=("AlarmTime",),
        root_name="OneClickAlarmConfig",
        fallback_field="AlarmTime",
        native_min_value=0,
        native_max_value=600,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="push_interval_motion",
        translation_key="push_interval_motion",
        path=ENDPOINT_PUSH_INTERVAL,
        aliases=("Motion",),
        root_name="PushEventInterval",
        fallback_field="Motion",
        native_min_value=0,
        native_max_value=86400,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="push_interval_people",
        translation_key="push_interval_people",
        path=ENDPOINT_PUSH_INTERVAL,
        aliases=("People",),
        root_name="PushEventInterval",
        fallback_field="People",
        native_min_value=0,
        native_max_value=86400,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.BOX,
    ),
    HiEasyNumberDescription(
        key="ircut_sensitivity",
        translation_key="ircut_sensitivity",
        path=ENDPOINT_IRCUT,
        aliases=("Sensitivity",),
        root_name="IrCutFillter",
        fallback_field="Sensitivity",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
    HiEasyNumberDescription(
        key="image_noise_reduce",
        translation_key="image_noise_reduce",
        path=ENDPOINT_IMAGE_BASIC,
        aliases=("NoiseReduce",),
        root_name="Basic",
        fallback_field="NoiseReduce",
        native_min_value=0,
        native_max_value=255,
        native_step=1,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numeric settings."""
    coordinator = entry.runtime_data
    entities: list[HiEasyNumber] = []
    for runtime in coordinator.devices.values():
        did = runtime.cloud.did
        entities.extend(
            HiEasyNumber(coordinator, did, description)
            for description in DEVICE_NUMBERS
        )
        for channel in range(1, min(runtime.cloud.channel_count, 8) + 1):
            for template in CHANNEL_NUMBERS:
                description = HiEasyNumberDescription(
                    key=f"{template.key}_{channel}",
                    translation_key=template.translation_key,
                    path=template.path.format(channel=channel),
                    aliases=template.aliases,
                    root_name=template.root_name,
                    fallback_field=template.fallback_field,
                    channel=channel,
                    native_min_value=template.native_min_value,
                    native_max_value=template.native_max_value,
                    native_step=template.native_step,
                    native_unit_of_measurement=template.native_unit_of_measurement,
                    mode=template.mode,
                )
                entities.append(HiEasyNumber(coordinator, did, description))
    async_add_entities(entities)


class HiEasyNumber(HiEasyLocalEntity, NumberEntity):
    """Represent a numeric HiEasy setting."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: HiEasyNumberDescription

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasyNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        if description.channel is not None:
            self._attr_translation_placeholders = {"channel": str(description.channel)}

    @property
    def native_value(self) -> float | None:
        """Return the current numeric setting."""
        value = xml_value(
            self.runtime,
            self.entity_description.path,
            *self.entity_description.aliases,
        )
        return _to_number(value)

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

    async def async_set_native_value(self, value: float) -> None:
        """Write the numeric setting."""
        if value.is_integer():
            stored: str | float = str(int(value))
        else:
            stored = str(value)
        await self.coordinator.async_set_value(
            self.did,
            self.entity_description.path,
            stored,
            aliases=self.entity_description.aliases,
            root_name=self.entity_description.root_name,
            fallback_field=self.entity_description.fallback_field,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the backing CGI path."""
        return {"cgi_path": self.entity_description.path}
