"""Shared Home Assistant entity helpers for HiEasy devices."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HiEasyCoordinator
from .models import DeviceRuntime


class HiEasyEntity(CoordinatorEntity[HiEasyCoordinator]):
    """Base entity associated with one cloud device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HiEasyCoordinator,
        did: str,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.did = did
        self._entity_key = key
        self._attr_unique_id = f"{did.lower()}_{key}"

    @property
    def runtime(self) -> DeviceRuntime | None:
        """Return current device runtime."""
        return self.coordinator.devices.get(self.did.lower())

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared device registry information."""
        runtime = self.runtime
        cloud = runtime.cloud if runtime else None
        return DeviceInfo(
            identifiers={(DOMAIN, self.did.lower())},
            name=cloud.name if cloud else self.did,
            manufacturer=MANUFACTURER,
            model=cloud.model if cloud else None,
            sw_version=cloud.firmware if cloud else None,
            serial_number=cloud.serial if cloud else None,
        )

    @property
    def available(self) -> bool:
        """Return cloud coordinator availability."""
        return super().available and self.runtime is not None


class HiEasyLocalEntity(HiEasyEntity):
    """Base entity which requires a reachable local endpoint."""

    @property
    def available(self) -> bool:
        """Return local endpoint availability."""
        runtime = self.runtime
        return super().available and runtime is not None and runtime.lan is not None and runtime.lan.online


def xml_value(runtime: DeviceRuntime | None, path: str, *names: str) -> Any:
    """Find a value in flattened local XML state."""
    if runtime is None or runtime.lan is None:
        return None
    values = runtime.lan.values
    for name in names:
        target = name.lower()
        for key, value in values.items():
            lowered = key.lower()
            if path and not lowered.startswith(f"{path.lower()}:"):
                continue
            if lowered.rsplit(":", 1)[-1].rsplit(".", 1)[-1] == target:
                return value
    return None


def xml_value_any(runtime: DeviceRuntime | None, path: str, names: tuple[str, ...]) -> Any:
    """Find the first value among aliases."""
    return xml_value(runtime, path, *names)
