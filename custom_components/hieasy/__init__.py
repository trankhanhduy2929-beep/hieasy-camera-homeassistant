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
    ATTR_CHANNEL,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DID,
    ATTR_METHOD,
    ATTR_PATH,
    ATTR_PRESET,
    ATTR_XML,
    DATA_COORDINATORS,
    DOMAIN,
    PLATFORMS,
    SERVICE_GOTO_PRESET,
    SERVICE_REDISCOVER,
    SERVICE_SEND_COMMAND,
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
