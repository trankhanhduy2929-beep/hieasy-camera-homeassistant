"""Config flow for the HiEasy integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, selector

from .api import (
    HiEasyApiError,
    HiEasyCannotConnectError,
    HiEasyCloudClient,
    HiEasyInvalidAuthError,
    normalize_account,
)
from .const import (
    CONF_ACCOUNT,
    CONF_DISCOVER_LAN,
    CONF_LAN_HOSTS,
    CONF_LAN_NETWORKS,
    CONF_MAX_SCAN_HOSTS,
    CONF_REGION,
    CONF_RTSP_PATHS,
    CONF_RTSP_PORTS,
    CONF_SCAN_PORTS,
    CONF_SCAN_TIMEOUT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DISCOVER_LAN,
    DEFAULT_MAX_SCAN_HOSTS,
    DEFAULT_RTSP_PATHS,
    DEFAULT_RTSP_PORTS,
    DEFAULT_SCAN_PORTS,
    DEFAULT_SCAN_TIMEOUT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    REGION_AMERICA,
    REGION_AUTO,
    REGION_CHINA,
    REGION_EUROPE,
    REGION_WORLD,
    REGION_YL,
)

REGION_OPTIONS = [
    REGION_AUTO,
    REGION_WORLD,
    REGION_AMERICA,
    REGION_EUROPE,
    REGION_CHINA,
    REGION_YL,
]

_AUTH_ERROR_KEYS = {
    REGION_WORLD: "invalid_auth_world",
    REGION_AMERICA: "invalid_auth_america",
    REGION_EUROPE: "invalid_auth_europe",
    REGION_CHINA: "invalid_auth_china",
    REGION_YL: "invalid_auth_yl",
}

_LOGGER = logging.getLogger(__name__)


def _auth_error_key(error: HiEasyInvalidAuthError) -> str:
    """Return an actionable config-flow error for the rejected region."""
    if error.code == 2011 and error.region in _AUTH_ERROR_KEYS:
        return _AUTH_ERROR_KEYS[error.region]
    return "invalid_auth"


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_ACCOUNT,
                default=values.get(CONF_ACCOUNT, ""),
            ): selector.TextSelector(),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_REGION,
                default=values.get(CONF_REGION, REGION_AUTO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=REGION_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="region",
                )
            ),
        }
    )


async def _async_validate(hass, data: Mapping[str, Any]) -> tuple[str, int]:
    session = aiohttp_client.async_get_clientsession(hass)
    client = HiEasyCloudClient(
        session,
        str(data[CONF_ACCOUNT]),
        str(data[CONF_PASSWORD]),
        str(data.get(CONF_REGION, REGION_AUTO)),
    )
    login = await client.async_login()
    devices = await client.async_get_devices()
    if not devices:
        raise ValueError("no_devices")
    return login.region, len(devices)


class HiEasyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle account setup and reauthentication."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return HiEasyOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Validate an account and create the config entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                active_region, device_count = await _async_validate(self.hass, user_input)
            except HiEasyInvalidAuthError as err:
                errors["base"] = _auth_error_key(err)
            except HiEasyCannotConnectError:
                errors["base"] = "cannot_connect"
            except ValueError as err:
                errors["base"] = str(err)
            except HiEasyApiError:
                errors["base"] = "api_error"
            except Exception:
                _LOGGER.exception("Unexpected error while validating HiEasy account")
                errors["base"] = "unknown"
            else:
                account = normalize_account(str(user_input[CONF_ACCOUNT]))
                await self.async_set_unique_id(f"{account.lower()}:{active_region}")
                self._abort_if_unique_id_configured()
                data = dict(user_input)
                data[CONF_ACCOUNT] = account
                data[CONF_REGION] = active_region
                return self.async_create_entry(
                    title=account,
                    data=data,
                    description_placeholders={"device_count": str(device_count)},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Validate a replacement password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                active_region, _device_count = await _async_validate(self.hass, data)
            except HiEasyInvalidAuthError as err:
                errors["base"] = _auth_error_key(err)
            except HiEasyCannotConnectError:
                errors["base"] = "cannot_connect"
            except (HiEasyApiError, ValueError):
                errors["base"] = "api_error"
            except Exception:
                _LOGGER.exception("Unexpected error while reauthenticating HiEasy")
                errors["base"] = "unknown"
            else:
                data[CONF_ACCOUNT] = normalize_account(str(data[CONF_ACCOUNT]))
                data[CONF_REGION] = active_region
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={"account": str(entry.data[CONF_ACCOUNT])},
        )


class HiEasyOptionsFlow(OptionsFlow):
    """Configure bounded LAN discovery and polling."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DISCOVER_LAN,
                    default=current.get(CONF_DISCOVER_LAN, DEFAULT_DISCOVER_LAN),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_LAN_NETWORKS,
                    default=current.get(CONF_LAN_NETWORKS, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_LAN_HOSTS,
                    default=current.get(CONF_LAN_HOSTS, ""),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_SCAN_PORTS,
                    default=current.get(CONF_SCAN_PORTS, DEFAULT_SCAN_PORTS),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_RTSP_PORTS,
                    default=current.get(CONF_RTSP_PORTS, DEFAULT_RTSP_PORTS),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_RTSP_PATHS,
                    default=current.get(CONF_RTSP_PATHS, DEFAULT_RTSP_PATHS),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_SCAN_TIMEOUT,
                    default=current.get(CONF_SCAN_TIMEOUT, DEFAULT_SCAN_TIMEOUT),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.2,
                        max=5.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_SCAN_HOSTS,
                    default=current.get(CONF_MAX_SCAN_HOSTS, DEFAULT_MAX_SCAN_HOSTS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=1024,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL,
                        max=MAX_UPDATE_INTERVAL,
                        step=10,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
