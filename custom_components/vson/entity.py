"""Base entity classes for the VSON integration."""

from __future__ import annotations

from functools import cached_property
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VsonCoordinator
from .devices import VsonDevice


def build_device_info(coordinator: VsonCoordinator, device_id: str) -> DeviceInfo:
    """Build the DeviceInfo for a device from the coordinator data."""
    data = getattr(coordinator, "data", None)
    dev: VsonDevice | None = data.get(device_id) if data else None
    family = dev.family if dev else None
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=dev.name if dev else device_id,
        manufacturer=family.manufacturer if family else "VSON",
        model=family.model if family else "VSON device",
        model_id=dev.type_code if dev else None,
        sw_version=str(dev.value("version")) if dev and dev.value("version") else None,
    )


class ReefRoleMixin:
    """Expose ``translation_key`` as a stable ``reef_role`` state attribute.

    The attribute name is shared across the ReefTech ecosystem: ha-reef-card
    and the shared blueprints discover entities by scanning ``hass.states`` for
    this attribute, with no per-integration configuration. Publishing it is all
    it takes for VSON entities to appear in the same views.

    Must come FIRST in the MRO so this property wins over the default one.
    """

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        base = getattr(self, "_attr_extra_state_attributes", None) or {}
        tk = getattr(self, "translation_key", None)
        if tk:
            return {**base, "reef_role": tk}
        return dict(base) if base else None


class VsonEntity(CoordinatorEntity[VsonCoordinator]):
    """Base class for all VSON entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VsonCoordinator,
        device_id: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{unique_suffix}"

    @property
    def _device(self) -> VsonDevice | None:
        return (
            self.coordinator.data.get(self._device_id)
            if self.coordinator.data
            else None
        )

    def _value(self, key: str, default: Any = None) -> Any:
        dev = self._device
        return dev.value(key, default) if dev else default

    @cached_property
    def device_info(self) -> DeviceInfo:  # type: ignore[reportIncompatibleVariableOverride]
        return build_device_info(self.coordinator, self._device_id)

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        # is_online is tri-state: None (unknown) is treated as available.
        return bool(
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online is not False
        )
