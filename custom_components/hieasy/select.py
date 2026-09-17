"""Select entities for HiEasy XML settings."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ENDPOINT_NIGHT_VISION
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


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HiEasy select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        HiEasyNightVisionSelect(coordinator, runtime.cloud.did)
        for runtime in coordinator.devices.values()
    )


class HiEasyNightVisionSelect(HiEasyLocalEntity, SelectEntity):
    """Select the raw NightVisionMode value accepted by the camera."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "night_vision_mode"

    def __init__(self, coordinator, did: str) -> None:
        super().__init__(coordinator, did, "night_vision_mode")

    @property
    def current_option(self) -> str | None:
        """Return the current raw mode."""
        value = xml_value(
            self.runtime,
            ENDPOINT_NIGHT_VISION,
            "NightVisionMode",
            "Mode",
        )
        return str(value) if value is not None else None

    @property
    def options(self) -> list[str]:
        """Return common modes plus the device's current vendor-specific value."""
        values = list(_COMMON_NIGHT_MODES)
        current = self.current_option
        if current and current not in values:
            values.insert(0, current)
        return values

    @property
    def available(self) -> bool:
        """Require the night-vision endpoint to be supported."""
        runtime = self.runtime
        return (
            super().available
            and runtime is not None
            and runtime.lan is not None
            and ENDPOINT_NIGHT_VISION in runtime.lan.xml
        )

    async def async_select_option(self, option: str) -> None:
        """Write NightVisionMode while preserving the rest of the XML."""
        await self.coordinator.async_set_value(
            self.did,
            ENDPOINT_NIGHT_VISION,
            option,
            aliases=("NightVisionMode", "Mode"),
            root_name="DeviceNightVisionCfg",
            fallback_field="NightVisionMode",
        )

