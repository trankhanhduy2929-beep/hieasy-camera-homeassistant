"""Home Assistant integration for HiEasy/Visioncop cameras."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import (
    ATTR_ACTION,
    ATTR_CHANNEL,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DID,
    ATTR_DURATION,
    ATTR_METHOD,
    ATTR_PATH,
    ATTR_PRESET,
    ATTR_TEXT,
    ATTR_XML,
    DATA_COORDINATORS,
    DOMAIN,
    PLATFORMS,
    SERVICE_ALARM_OUTPUT,
    SERVICE_AUDIO_ALARM_STOP,
    SERVICE_FORCE_IFRAME,
    SERVICE_FORMAT_SDCARD,
    SERVICE_GOTO_PRESET,
    SERVICE_ONE_CLICK_ALARM,
    SERVICE_PTZ_CONTROL,
    SERVICE_REDISCOVER,
    SERVICE_SEND_COMMAND,
    SERVICE_SET_OSD_TEXT,
    SERVICE_SLEEP_CONTROL,
    SERVICE_SYNC_TIME,
    SERVICE_WIFI_SCAN,
    SERVICE_WIFI_STATUS,
)
from .coordinator import HiEasyCoordinator

_LOGGER = logging.getLogger(__name__)
_LEGACY_LAST_SEEN_OPTION = "last_seen_interval"

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_DID): cv.string,
        vol.Required(ATTR_PATH): cv.string,
        vol.Optional(ATTR_METHOD, default="GET"): vol.In({"GET", "PUT", "POST"}),
        vol.Optional(ATTR_XML): cv.string,
    }
)
REDISCOVER_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})
PRESET_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_DID): cv.string,
        vol.Required(ATTR_CHANNEL, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_PRESET): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
PTZ_CONTROL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_DID): cv.string,
        vol.Required(ATTR_CHANNEL, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_ACTION): cv.string,
        vol.Optional(ATTR_PRESET): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_DID): cv.string,
        vol.Optional(ATTR_CHANNEL, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_ACTION): cv.string,
        vol.Optional(ATTR_TEXT): cv.string,
        vol.Optional(ATTR_DURATION): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(ATTR_PRESET): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


async def async_setup(hass: HomeAssistant, _config: Mapping[str, Any]) -> bool:
    """Set up services shared by all HiEasy config entries."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(DATA_COORDINATORS, {})
    if domain_data.get("services_registered"):
        return True

    async def send_command(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        response = await coordinator.async_send_command(
            call.data[ATTR_DID],
            call.data[ATTR_PATH],
            call.data[ATTR_METHOD],
            call.data.get(ATTR_XML),
        )
        return {"did": call.data[ATTR_DID], "path": call.data[ATTR_PATH], "response": response}

    async def rediscover(call: ServiceCall) -> dict[str, Any]:
        coordinators = _coordinators_for_call(hass, call)
        await _gather(*(coordinator.async_force_rediscovery() for coordinator in coordinators))
        return {"entries": len(coordinators)}

    async def goto_preset(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_goto_preset(
            call.data[ATTR_DID],
            call.data[ATTR_CHANNEL],
            call.data[ATTR_PRESET],
        )
        return {
            "did": call.data[ATTR_DID],
            "channel": call.data[ATTR_CHANNEL],
            "preset": call.data[ATTR_PRESET],
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        send_command,
        schema=SEND_COMMAND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REDISCOVER,
        rediscover,
        schema=REDISCOVER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GOTO_PRESET,
        goto_preset,
        schema=PRESET_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def ptz_control(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        action = str(call.data[ATTR_ACTION])
        channel = int(call.data[ATTR_CHANNEL])
        preset = call.data.get(ATTR_PRESET)
        await _ptz_action(coordinator, call.data[ATTR_DID], channel, action, preset)
        return {"did": call.data[ATTR_DID], "channel": channel, "action": action}

    async def one_click_alarm(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_send_command(
            call.data[ATTR_DID],
            f"/Alarm/{call.data[ATTR_CHANNEL]}/OneClickAlarmControl",
            "POST",
            "",
        )
        return {"did": call.data[ATTR_DID]}

    async def audio_alarm_stop(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_send_command(
            call.data[ATTR_DID],
            f"/System/{call.data[ATTR_CHANNEL]}/AudioAlarmEliminate",
            "PUT",
            "<AudioAlarmEliminate><Enable>true</Enable></AudioAlarmEliminate>",
        )
        return {"did": call.data[ATTR_DID]}

    async def alarm_output(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        action = str(call.data.get(ATTR_ACTION, "on")).lower()
        channel = int(call.data[ATTR_CHANNEL])
        await coordinator.async_send_command(
            call.data[ATTR_DID],
            f"/System/{channel}/RemoteAlarmoutControl/{action}",
            "PUT",
            "",
        )
        return {"did": call.data[ATTR_DID], "action": action}

    async def sleep_control(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        action = str(call.data.get(ATTR_ACTION, "sleep")).lower()
        value = "1" if action in {"sleep", "1", "on"} else "0"
        await coordinator.async_send_command(
            call.data[ATTR_DID],
            "/System/DeviceSleepControl",
            "PUT",
            f"<DeviceSleepControl><SleepControl>{value}</SleepControl></DeviceSleepControl>",
        )
        return {"did": call.data[ATTR_DID], "action": action}

    async def format_sdcard(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_send_command(
            call.data[ATTR_DID], "/Record/Format/Call", "PUT", ""
        )
        return {"did": call.data[ATTR_DID]}

    async def force_iframe(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_send_command(
            call.data[ATTR_DID],
            f"/System/{call.data[ATTR_CHANNEL]}/RemoteForceIFrame",
            "PUT",
            "",
        )
        return {"did": call.data[ATTR_DID]}

    async def sync_time(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_sync_time(call.data[ATTR_DID])
        return {"did": call.data[ATTR_DID]}

    async def set_osd_text(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        channel = int(call.data[ATTR_CHANNEL])
        text = str(call.data[ATTR_TEXT])
        path = f"/Pictures/{channel}/OSD"
        runtime = coordinator.runtime_for_did(call.data[ATTR_DID])
        old_xml = runtime.lan.xml.get(path, "") if runtime.lan else ""
        if not old_xml:
            old_xml = (
                "<OSD><DisplayName><Enable>true</Enable>"
                "<Name></Name></DisplayName></OSD>"
            )
        new_xml = _set_osd_name(old_xml, text)
        await coordinator.async_send_command(call.data[ATTR_DID], path, "PUT", new_xml)
        return {"did": call.data[ATTR_DID], "channel": channel}

    hass.services.async_register(
        DOMAIN, SERVICE_PTZ_CONTROL, ptz_control,
        schema=PTZ_CONTROL_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ONE_CLICK_ALARM, one_click_alarm,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_AUDIO_ALARM_STOP, audio_alarm_stop,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ALARM_OUTPUT, alarm_output,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SLEEP_CONTROL, sleep_control,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_FORMAT_SDCARD, format_sdcard,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_FORCE_IFRAME, force_iframe,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_TIME, sync_time,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_OSD_TEXT, set_osd_text,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )

    async def wifi_scan(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        xml_text = await coordinator.async_send_command(
            call.data[ATTR_DID],
            "/Network/Interfaces/2/WIFIAccessPointList",
            "GET",
            None,
        )
        return {"did": call.data[ATTR_DID], "xml": xml_text, "aps": _parse_ap_list(xml_text)}

    async def wifi_status(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_for_call(hass, call)
        xml_text = await coordinator.async_send_command(
            call.data[ATTR_DID],
            "/Network/Interfaces/2/WirelessEx",
            "GET",
            None,
        )
        return {"did": call.data[ATTR_DID], "xml": xml_text, **_flatten_wireless_ex(xml_text)}

    hass.services.async_register(
        DOMAIN, SERVICE_WIFI_SCAN, wifi_scan,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_WIFI_STATUS, wifi_status,
        schema=ACTION_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    domain_data["services_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one HiEasy account."""
    _remove_legacy_last_seen(hass, entry)
    session = aiohttp_client.async_get_clientsession(hass)
    coordinator = HiEasyCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(DATA_COORDINATORS, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _remove_legacy_last_seen(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the retired timestamp sensor and its stored option."""
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity_entry.entity_id.startswith("sensor.")
            and entity_entry.unique_id.lower().endswith("_last_seen")
        ):
            registry.async_remove(entity_entry.entity_id)

    if _LEGACY_LAST_SEEN_OPTION in entry.options:
        options = dict(entry.options)
        options.pop(_LEGACY_LAST_SEEN_OPTION, None)
        hass.config_entries.async_update_entry(entry, options=options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one HiEasy account."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = entry.runtime_data
    if unloaded:
        await coordinator.async_shutdown()
        hass.data.get(DOMAIN, {}).get(DATA_COORDINATORS, {}).pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _coordinators_for_call(hass: HomeAssistant, call: ServiceCall) -> list[HiEasyCoordinator]:
    """Select coordinators by optional config entry id."""
    coordinators: dict[str, HiEasyCoordinator] = hass.data.get(DOMAIN, {}).get(
        DATA_COORDINATORS, {}
    )
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise ServiceValidationError(f"Không tìm thấy config entry {entry_id}")
        return [coordinator]
    return list(coordinators.values())


def _coordinator_for_call(hass: HomeAssistant, call: ServiceCall) -> HiEasyCoordinator:
    """Select the entry containing a requested DID."""
    candidates = _coordinators_for_call(hass, call)
    did = str(call.data.get(ATTR_DID, "")).lower()
    matches = [coordinator for coordinator in candidates if did in coordinator.devices]
    if len(matches) == 1:
        return matches[0]
    if not candidates:
        raise ServiceValidationError("Chưa có config entry HiEasy đang hoạt động")
    if len(candidates) == 1:
        return candidates[0]
    raise ServiceValidationError(
        "DID không duy nhất; hãy chỉ rõ config_entry_id trong dịch vụ HiEasy"
    )


async def _gather(*awaitables) -> None:
    """Await a collection while allowing all entries to refresh together."""
    import asyncio

    if awaitables:
        await asyncio.gather(*awaitables)


async def _ptz_action(
    coordinator: HiEasyCoordinator,
    did: str,
    channel: int,
    action: str,
    preset: int | None,
) -> None:
    """Run a PTZ sub-action using the APK command payloads."""
    normalized = action.strip().lower().replace("-", "_")
    param = f"Param1={preset}" if preset is not None else "Param1=1"
    mapping = {
        "preset_set": (f"/PTZ/{channel}/Presets/Set", param),
        "preset_remove": (f"/PTZ/{channel}/Presets/Remove", param),
        "ptz_reset": (f"/PTZ/{channel}/PTZReset", ""),
        "lens_reset": (f"/PTZ/{channel}/CameraLensReset", ""),
        "calibration": (f"/PTZ/{channel}/Calibration", ""),
        "cruise_start": (f"/PTZ/{channel}/Cruise/StartCruise", "Param1=1"),
        "cruise_stop": (f"/PTZ/{channel}/Cruise/StopCruise", "Param1=1"),
        "cruise_track_start": (f"/PTZ/{channel}/Cruise/CruiseTrackStart", "Param1=1"),
        "cruise_track_stop": (f"/PTZ/{channel}/Cruise/CruiseTrackStop", "Param1=1"),
        "human_track_start": (f"/PTZ/{channel}/HumanTrack/StartHumanTrack", "Param1=1"),
        "human_track_stop": (f"/PTZ/{channel}/HumanTrack/StopHumanTrack", "Param1=1"),
        "range_scan_start": (f"/PTZ/{channel}/RangeScan/StartRangeScan", "Param1=1"),
        "range_scan_stop": (f"/PTZ/{channel}/RangeScan/StopRangeScan", "Param1=1"),
        "range_scan_left": (f"/PTZ/{channel}/RangeScan/RangeScanSetLeftBoundary", "Param1=1"),
        "range_scan_right": (f"/PTZ/{channel}/RangeScan/RangeScanSetRightBoundary", "Param1=1"),
        "range_scan360_start": (f"/PTZ/{channel}/RangeScan/StartRangeScan360", "Param1=1"),
        "range_scan360_stop": (f"/PTZ/{channel}/RangeScan/StopRangeScan360", "Param1=1"),
        "track_start": (f"/PTZ/{channel}/Track/StartTrack", "Param1=1"),
        "track_stop": (f"/PTZ/{channel}/Track/StopTrack", "Param1=1"),
        "track_mem_start": (f"/PTZ/{channel}/Track/StartTrackMem", "Param1=1"),
        "track_mem_stop": (f"/PTZ/{channel}/Track/StopTrackMem", "Param1=1"),
        "watch_start": (f"/PTZ/{channel}/Watch/StartWatch", param),
        "watch_stop": (f"/PTZ/{channel}/Watch/StopWatch", param),
        "watch_care_goto": ("/PTZ/1/WatchCareGoto", "Param1=1"),
        "wiper": (f"/PTZ/{channel}/RainBrush", "Param1=1"),
        "heater": (f"/PTZ/{channel}/Hearter", "Param1=1"),
    }
    target = mapping.get(normalized)
    if target is None:
        raise ServiceValidationError(
            f"PTZ action không hỗ trợ: {action}. Hỗ trợ: {sorted(mapping)}"
        )
    await coordinator.async_send_command(did, target[0], "PUT", target[1])


def _set_osd_name(xml_text: str, name: str) -> str:
    """Replace the OSD DisplayName/Name value in an OSD XML body."""
    import re
    import xml.sax.saxutils

    escaped = xml.sax.saxutils.escape(name)
    if "<Name>" in xml_text or "<Name " in xml_text:
        return re.sub(
            r"<Name([^>]*)>.*?</Name>",
            f"<Name\\1>{escaped}</Name>",
            xml_text,
            count=1,
            flags=re.DOTALL,
        )
    if "<DisplayName>" in xml_text:
        return xml_text.replace(
            "<DisplayName>", f"<DisplayName><Name>{escaped}</Name>", 1
        )
    if "</OSD>" in xml_text:
        return xml_text.replace(
            "</OSD>",
            f"<DisplayName><Enable>true</Enable><Name>{escaped}</Name></DisplayName></OSD>",
            1,
        )
    return (
        f"<OSD><DisplayName><Enable>true</Enable><Name>{escaped}</Name>"
        "</DisplayName></OSD>"
    )


def _parse_ap_list(xml_text: str) -> list[dict[str, str]]:
    """Parse WIFIAccessPointList XML into a list of access point dicts."""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    aps: list[dict[str, str]] = []
    for ap in root.iter():
        tag = ap.tag.rsplit("}", 1)[-1]
        if tag != "AP":
            continue
        entry: dict[str, str] = {}
        for child in ap:
            child_tag = child.tag.rsplit("}", 1)[-1]
            entry[child_tag] = (child.text or "").strip()
        if entry:
            aps.append(entry)
    return aps


def _flatten_wireless_ex(xml_text: str) -> dict[str, Any]:
    """Extract WifiName/WifiSignalStrength from a WirelessEx response."""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    out: dict[str, Any] = {}
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        text = (elem.text or "").strip()
        if not text:
            continue
        if tag == "WifiName":
            out["ssid"] = text
        elif tag == "WifiSignalStrength":
            try:
                out["signal_strength"] = int(text)
            except ValueError:
                out["signal_strength"] = text
        else:
            out[tag] = text
    return out
