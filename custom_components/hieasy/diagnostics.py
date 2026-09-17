"""Diagnostics support for HiEasy without exposing account passwords."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_ACCOUNT, CONF_REGION

TO_REDACT = {
    "pwd",
    "password",
    "passwd",
    "token",
    "authorization",
    "Authorization",
    "account",
    CONF_ACCOUNT,
}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return redacted integration diagnostics."""
    coordinator = entry.runtime_data
    devices: list[dict[str, Any]] = []
    for runtime in coordinator.devices.values():
        cloud = runtime.cloud
        lan = runtime.lan
        devices.append(
            {
                "did": cloud.did,
                "name": cloud.name,
                "model": cloud.model,
                "serial": cloud.serial,
                "mac": cloud.mac,
                "channel_count": cloud.channel_count,
                "cloud_status": cloud.cloud_status,
                "lan": {
                    "host": lan.host if lan else None,
                    "scheme": lan.scheme if lan else None,
                    "http_port": lan.http_port if lan else None,
                    "command_port": lan.command_port if lan else None,
                    "media_port": lan.media_port if lan else None,
                    "transport": lan.transport if lan else None,
                    "online": lan.online if lan else False,
                    "stream_count": len(lan.streams) if lan else 0,
                    "identity": dict(lan.identity) if lan else {},
                    "last_error": lan.last_error if lan else None,
                },
            }
        )
    return async_redact_data(
        {
            "entry": {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "data": {CONF_ACCOUNT: entry.data.get(CONF_ACCOUNT), CONF_REGION: entry.data.get(CONF_REGION)},
                "options": dict(entry.options),
            },
            "coordinator": coordinator.diagnostic_data(),
            "devices": devices,
        },
        TO_REDACT,
    )

