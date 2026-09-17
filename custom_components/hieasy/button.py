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


BUTTONS: tuple[HiEasyButtonDescription, ...] = (
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
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        HiEasyButton(coordinator, runtime.cloud.did, description)
        for runtime in coordinator.devices.values()
        for description in BUTTONS
    )


class HiEasyButton(HiEasyEntity, ButtonEntity):
    """Represent a HiEasy device action."""

    entity_description: HiEasyButtonDescription

    def __init__(self, coordinator, did: str, description: HiEasyButtonDescription) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description

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
        if self.entity_description.action == "rediscover":
            await self.coordinator.async_force_rediscovery()
            return
        if self.entity_description.action == "reboot":
            await self.coordinator.async_reboot_device(self.did)
