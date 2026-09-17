"""Writable HiEasy XML configuration switches."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ENDPOINT_ALARM_OUT,
    ENDPOINT_ANIMAL_DETECT,
    ENDPOINT_ARI_DECT,
    ENDPOINT_ATMOSPHERE_LIGHT,
    ENDPOINT_CAR_DETECT,
    ENDPOINT_CRY_DETECT,
    ENDPOINT_DND,
    ENDPOINT_EBIKE_DETECT,
    ENDPOINT_FIRE_DETECT,
    ENDPOINT_INDICATOR,
    ENDPOINT_INTELLIGENT_TRACK,
    ENDPOINT_LIGHT_CONTROL,
    ENDPOINT_LIGHT_WARNING,
    ENDPOINT_MOTION,
    ENDPOINT_MOVE_TRACK,
    ENDPOINT_NIGHT_LED,
    ENDPOINT_ONE_CLICK_ALARM_CFG,
    ENDPOINT_PEOPLE_DETECT,
    ENDPOINT_PIR,
    ENDPOINT_RADAR,
    ENDPOINT_RECORD_SCHEDULE,
    ENDPOINT_VOICE_LIGHT_CONFIG,
    ENDPOINT_WHITE_LIGHT,
)
from .entity import HiEasyLocalEntity, xml_value
from .protocol import parse_bool


@dataclass(frozen=True, kw_only=True)
class HiEasySwitchDescription(SwitchEntityDescription):
    """Describe one XML-backed switch."""

    path: str
    aliases: Sequence[str]
    root_name: str
    fallback_field: str = "Enable"
    channel: int | None = None


DEVICE_SWITCHES: tuple[HiEasySwitchDescription, ...] = (
    HiEasySwitchDescription(
        key="indicator_light",
        translation_key="indicator_light",
        path=ENDPOINT_INDICATOR,
        aliases=("Enable", "Enabled"),
        root_name="IndicatorLightCfg",
    ),
    HiEasySwitchDescription(
        key="light_control",
        translation_key="light_control",
        path=ENDPOINT_LIGHT_CONTROL,
        aliases=("Enable", "Enabled", "LightEnable", "State"),
        root_name="LightControlCfg",
    ),
    HiEasySwitchDescription(
        key="alarm_output",
        translation_key="alarm_output",
        path=ENDPOINT_ALARM_OUT,
        aliases=("State", "Enable", "Enabled"),
        root_name="AlarmOut",
        fallback_field="State",
    ),
    HiEasySwitchDescription(
        key="white_light",
        translation_key="white_light",
        path=ENDPOINT_WHITE_LIGHT,
        aliases=("Enable", "Enabled"),
        root_name="WhiteLightEnable",
    ),
    HiEasySwitchDescription(
        key="night_led",
        translation_key="night_led",
        path=ENDPOINT_NIGHT_LED,
        aliases=("Enable", "Enabled"),
        root_name="NightLedInfo",
    ),
    HiEasySwitchDescription(
        key="atmosphere_light",
        translation_key="atmosphere_light",
        path=ENDPOINT_ATMOSPHERE_LIGHT,
        aliases=("Enable", "Enabled"),
        root_name="AtmosphereLightCfg",
    ),
    HiEasySwitchDescription(
        key="do_not_disturb",
        translation_key="do_not_disturb",
        path=ENDPOINT_DND,
        aliases=("Enable", "Enabled"),
        root_name="DoNotDisturbMode",
    ),
    HiEasySwitchDescription(
        key="ari_dect_alarm",
        translation_key="ari_dect_alarm",
        path=ENDPOINT_ARI_DECT,
        aliases=("Enable", "Enabled"),
        root_name="AriDectAudioLightAlarm",
    ),
    HiEasySwitchDescription(
        key="cry_detect",
        translation_key="cry_detect",
        path=ENDPOINT_CRY_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="CryScreamDetect",
    ),
    HiEasySwitchDescription(
        key="intelligent_track",
        translation_key="intelligent_track",
        path=ENDPOINT_INTELLIGENT_TRACK,
        aliases=("Enable", "Enabled", "TrackAmplifySwitch"),
        root_name="AIIntelligentTrack",
    ),
    HiEasySwitchDescription(
        key="fire_detect",
        translation_key="fire_detect",
        path=ENDPOINT_FIRE_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="FireDetectCfgInfo",
    ),
    HiEasySwitchDescription(
        key="ebike_detect",
        translation_key="ebike_detect",
        path=ENDPOINT_EBIKE_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="EBikeDetectCfg",
    ),
)

CHANNEL_SWITCHES: tuple[HiEasySwitchDescription, ...] = (
    HiEasySwitchDescription(
        key="motion",
        translation_key="motion",
        path=ENDPOINT_MOTION,
        aliases=("Enable", "Enabled"),
        root_name="Motion",
    ),
    HiEasySwitchDescription(
        key="move_track",
        translation_key="move_track",
        path=ENDPOINT_MOVE_TRACK,
        aliases=("Enable", "Enabled"),
        root_name="MoveTrack",
    ),
    HiEasySwitchDescription(
        key="people_detect",
        translation_key="people_detect",
        path=ENDPOINT_PEOPLE_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="PeopleDetect",
    ),
    HiEasySwitchDescription(
        key="car_detect",
        translation_key="car_detect",
        path=ENDPOINT_CAR_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="CarDetect",
    ),
    HiEasySwitchDescription(
        key="animal_detect",
        translation_key="animal_detect",
        path=ENDPOINT_ANIMAL_DETECT,
        aliases=("Enable", "Enabled"),
        root_name="AnimalDetect",
    ),
    HiEasySwitchDescription(
        key="pir_detect",
        translation_key="pir_detect",
        path=ENDPOINT_PIR,
        aliases=("Enable", "Enabled"),
        root_name="PirDetect",
    ),
    HiEasySwitchDescription(
        key="radar_detect",
        translation_key="radar_detect",
        path=ENDPOINT_RADAR,
        aliases=("Enable", "Enabled"),
        root_name="RadarDetect",
    ),
    HiEasySwitchDescription(
        key="light_warning",
        translation_key="light_warning",
        path=ENDPOINT_LIGHT_WARNING,
        aliases=("Enable", "Enabled"),
        root_name="LightWarning",
    ),
    HiEasySwitchDescription(
        key="voice_light",
        translation_key="voice_light",
        path=ENDPOINT_VOICE_LIGHT_CONFIG,
        aliases=("IsVoiceOpen", "IsLightOpen", "Enable", "Enabled"),
        root_name="AlarmVoiceLightConfig",
        fallback_field="IsVoiceOpen",
    ),
    HiEasySwitchDescription(
        key="one_click_alarm",
        translation_key="one_click_alarm",
        path=ENDPOINT_ONE_CLICK_ALARM_CFG,
        aliases=("IsVoiceOpen", "IsLightOpen", "IsAlarmOutOpen", "Enable", "Enabled"),
        root_name="OneClickAlarmConfig",
        fallback_field="IsAlarmOutOpen",
    ),
    HiEasySwitchDescription(
        key="record_schedule",
        translation_key="record_schedule",
        path=ENDPOINT_RECORD_SCHEDULE,
        aliases=("Enable", "Enabled"),
        root_name="RecordScheduleV2",
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up common device and per-channel switches."""
    coordinator = entry.runtime_data
    entities: list[HiEasySwitch] = []
    for runtime in coordinator.devices.values():
        did = runtime.cloud.did
        entities.extend(
            HiEasySwitch(coordinator, did, description)
            for description in DEVICE_SWITCHES
        )
        for channel in range(1, min(runtime.cloud.channel_count, 8) + 1):
            for template in CHANNEL_SWITCHES:
                description = HiEasySwitchDescription(
                    key=f"{template.key}_{channel}",
                    translation_key=template.translation_key,
                    path=template.path.format(channel=channel),
                    aliases=template.aliases,
                    root_name=template.root_name,
                    fallback_field=template.fallback_field,
                    channel=channel,
                )
                entities.append(HiEasySwitch(coordinator, did, description))
    async_add_entities(entities)


class HiEasySwitch(HiEasyLocalEntity, SwitchEntity):
    """Represent one writable HiEasy setting."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        did: str,
        description: HiEasySwitchDescription,
    ) -> None:
        """Initialize the switch."""
        key = description.key
        super().__init__(coordinator, did, key)
        self.entity_description = description
        if description.channel is not None:
            self._attr_translation_placeholders = {"channel": str(description.channel)}

    @property
    def is_on(self) -> bool | None:
        """Return the current XML setting."""
        value = xml_value(
            self.runtime,
            self.entity_description.path,
            *self.entity_description.aliases,
        )
        return parse_bool(value)

    @property
    def available(self) -> bool:
        """Require a reachable local CGI endpoint."""
        runtime = self.runtime
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and runtime.lan.command_available
            and self.entity_description.path in runtime.lan.xml
        )

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable the setting."""
        await self.coordinator.async_set_enabled(
            self.did,
            self.entity_description.path,
            True,
            aliases=self.entity_description.aliases,
            root_name=self.entity_description.root_name,
            fallback_field=self.entity_description.fallback_field,
        )

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the setting."""
        await self.coordinator.async_set_enabled(
            self.did,
            self.entity_description.path,
            False,
            aliases=self.entity_description.aliases,
            root_name=self.entity_description.root_name,
            fallback_field=self.entity_description.fallback_field,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the backing CGI path."""
        return {"cgi_path": self.entity_description.path}
