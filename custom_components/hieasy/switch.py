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
    ENDPOINT_INDICATOR,
    ENDPOINT_LIGHT_CONTROL,
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
            (
                HiEasySwitch(
                    coordinator,
                    did,
                    HiEasySwitchDescription(
                        key="indicator_light",
                        translation_key="indicator_light",
                        path=ENDPOINT_INDICATOR,
                        aliases=("Enable", "Enabled"),
                        root_name="IndicatorLightCfg",
                    ),
                ),
                HiEasySwitch(
                    coordinator,
                    did,
                    HiEasySwitchDescription(
                        key="light_control",
                        translation_key="light_control",
                        path=ENDPOINT_LIGHT_CONTROL,
                        aliases=("Enable", "Enabled", "LightEnable", "State"),
                        root_name="LightControlCfg",
                    ),
                ),
                HiEasySwitch(
                    coordinator,
                    did,
                    HiEasySwitchDescription(
                        key="alarm_output",
                        translation_key="alarm_output",
                        path=ENDPOINT_ALARM_OUT,
                        aliases=("State", "Enable", "Enabled"),
                        root_name="AlarmOut",
                        fallback_field="State",
                    ),
                ),
            )
        )
        entities.extend(
            HiEasySwitch(
                coordinator,
                did,
                HiEasySwitchDescription(
                    key=f"motion_{channel}",
                    translation_key="motion",
                    path=f"/Pictures/{channel}/MoveTrack",
                    aliases=("Enable", "Enabled"),
                    root_name="Motion",
                    channel=channel,
                ),
            )
            for channel in range(1, min(runtime.cloud.channel_count, 8) + 1)
        )
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
        value = xml_value(self.runtime, self.entity_description.path, *self.entity_description.aliases)
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
