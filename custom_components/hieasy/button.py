"""Action buttons for HiEasy devices."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import HiEasyEntity


@dataclass(frozen=True, kw_only=True)
class HiEasyButtonDescription(ButtonEntityDescription):
    """Describe a HiEasy action button."""

    action: str
    local_required: bool = False
    channel: int | None = None
    payload: str | None = None


DEVICE_BUTTONS: tuple[HiEasyButtonDescription, ...] = (
    HiEasyButtonDescription(
        key="rediscover",
        translation_key="rediscover",
        action="rediscover",
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="reboot",
        translation_key="reboot",
        action="reboot",
        local_required=True,
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="force_iframe",
        translation_key="force_iframe",
        action="force_iframe",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="one_click_alarm",
        translation_key="one_click_alarm",
        action="one_click_alarm",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="audio_alarm_stop",
        translation_key="audio_alarm_stop",
        action="audio_alarm_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="sleep",
        translation_key="sleep",
        action="sleep",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="wake",
        translation_key="wake",
        action="wake",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="sync_time",
        translation_key="sync_time",
        action="sync_time",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="format_sdcard",
        translation_key="format_sdcard",
        action="format_sdcard",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="one_button_call",
        translation_key="one_button_call",
        action="one_button_call",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
)

CHANNEL_BUTTONS: tuple[HiEasyButtonDescription, ...] = (
    HiEasyButtonDescription(
        key="ptz_reset",
        translation_key="ptz_reset",
        action="ptz_reset",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="lens_reset",
        translation_key="lens_reset",
        action="lens_reset",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="ptz_calibration",
        translation_key="ptz_calibration",
        action="ptz_calibration",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="watch_care_goto",
        translation_key="watch_care_goto",
        action="watch_care_goto",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="cruise_start",
        translation_key="cruise_start",
        action="cruise_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="cruise_stop",
        translation_key="cruise_stop",
        action="cruise_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="cruise_track_start",
        translation_key="cruise_track_start",
        action="cruise_track_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="cruise_track_stop",
        translation_key="cruise_track_stop",
        action="cruise_track_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="human_track_start",
        translation_key="human_track_start",
        action="human_track_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="human_track_stop",
        translation_key="human_track_stop",
        action="human_track_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="range_scan_start",
        translation_key="range_scan_start",
        action="range_scan_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="range_scan_stop",
        translation_key="range_scan_stop",
        action="range_scan_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="range_scan360_start",
        translation_key="range_scan360_start",
        action="range_scan360_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="range_scan360_stop",
        translation_key="range_scan360_stop",
        action="range_scan360_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="track_start",
        translation_key="track_start",
        action="track_start",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="track_stop",
        translation_key="track_stop",
        action="track_stop",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="wiper",
        translation_key="wiper",
        action="wiper",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
    HiEasyButtonDescription(
        key="heater",
        translation_key="heater",
        action="heater",
        local_required=True,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy buttons."""
    coordinator = entry.runtime_data
    entities: list[HiEasyButton] = []
    for runtime in coordinator.devices.values():
        did = runtime.cloud.did
        entities.extend(
            HiEasyButton(coordinator, did, description)
            for description in DEVICE_BUTTONS
        )
        for channel in range(1, min(runtime.cloud.channel_count, 8) + 1):
            for template in CHANNEL_BUTTONS:
                description = HiEasyButtonDescription(
                    key=f"{template.key}_{channel}",
                    translation_key=template.translation_key,
                    action=template.action,
                    local_required=template.local_required,
                    entity_category=template.entity_category,
                    channel=channel,
                )
                entities.append(HiEasyButton(coordinator, did, description))
    async_add_entities(entities)


class HiEasyButton(HiEasyEntity, ButtonEntity):
    """Represent a HiEasy device action."""

    entity_description: HiEasyButtonDescription

    def __init__(self, coordinator, did: str, description: HiEasyButtonDescription) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        if description.channel is not None:
            self._attr_translation_placeholders = {"channel": str(description.channel)}

    @property
    def available(self) -> bool:
        """Require LAN only for local actions."""
        runtime = self.runtime
        return super().available and (
            not self.entity_description.local_required
            or bool(runtime and runtime.lan and runtime.lan.command_available)
        )

    async def async_press(self) -> None:
        """Run the configured action."""
        action = self.entity_description.action
        channel = self.entity_description.channel or 1
        if action == "rediscover":
            await self.coordinator.async_force_rediscovery()
        elif action == "reboot":
            await self.coordinator.async_reboot_device(self.did)
        elif action == "force_iframe":
            await self.coordinator.async_send_command(
                self.did, f"/System/{channel}/RemoteForceIFrame", "PUT", ""
            )
        elif action == "one_click_alarm":
            await self.coordinator.async_send_command(
                self.did, f"/Alarm/{channel}/OneClickAlarmControl", "POST", ""
            )
        elif action == "audio_alarm_stop":
            await self.coordinator.async_send_command(
                self.did,
                f"/System/{channel}/AudioAlarmEliminate",
                "PUT",
                "<AudioAlarmEliminate><Enable>true</Enable></AudioAlarmEliminate>",
            )
        elif action == "sleep":
            await self.coordinator.async_send_command(
                self.did,
                "/System/DeviceSleepControl",
                "PUT",
                "<DeviceSleepControl><SleepControl>1</SleepControl></DeviceSleepControl>",
            )
        elif action == "wake":
            await self.coordinator.async_send_command(
                self.did,
                "/System/DeviceSleepControl",
                "PUT",
                "<DeviceSleepControl><SleepControl>0</SleepControl></DeviceSleepControl>",
            )
        elif action == "sync_time":
            await self.coordinator.async_sync_time(self.did)
        elif action == "format_sdcard":
            await self.coordinator.async_send_command(
                self.did, "/Record/Format/Call", "PUT", ""
            )
        elif action == "one_button_call":
            await self.coordinator.async_send_command(
                self.did,
                "/System/DeviceOneButtonCall",
                "PUT",
                "<DeviceOneButtonCall><OneButtonCall>true</OneButtonCall></DeviceOneButtonCall>",
            )
        elif action == "ptz_reset":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/PTZReset", "PUT", ""
            )
        elif action == "lens_reset":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/CameraLensReset", "PUT", ""
            )
        elif action == "ptz_calibration":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Calibration", "PUT", ""
            )
        elif action == "watch_care_goto":
            await self.coordinator.async_send_command(
                self.did, "/PTZ/1/WatchCareGoto", "PUT", "Param1=1"
            )
        elif action == "cruise_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Cruise/StartCruise", "PUT", "Param1=1"
            )
        elif action == "cruise_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Cruise/StopCruise", "PUT", "Param1=1"
            )
        elif action == "cruise_track_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Cruise/CruiseTrackStart", "PUT", "Param1=1"
            )
        elif action == "cruise_track_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Cruise/CruiseTrackStop", "PUT", "Param1=1"
            )
        elif action == "human_track_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/HumanTrack/StartHumanTrack", "PUT", "Param1=1"
            )
        elif action == "human_track_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/HumanTrack/StopHumanTrack", "PUT", "Param1=1"
            )
        elif action == "range_scan_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/RangeScan/StartRangeScan", "PUT", "Param1=1"
            )
        elif action == "range_scan_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/RangeScan/StopRangeScan", "PUT", "Param1=1"
            )
        elif action == "range_scan360_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/RangeScan/StartRangeScan360", "PUT", "Param1=1"
            )
        elif action == "range_scan360_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/RangeScan/StopRangeScan360", "PUT", "Param1=1"
            )
        elif action == "track_start":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Track/StartTrack", "PUT", "Param1=1"
            )
        elif action == "track_stop":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Track/StopTrack", "PUT", "Param1=1"
            )
        elif action == "wiper":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/RainBrush", "PUT", "Param1=1"
            )
        elif action == "heater":
            await self.coordinator.async_send_command(
                self.did, f"/PTZ/{channel}/Hearter", "PUT", "Param1=1"
            )
