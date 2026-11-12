"""Binary sensor platform for VSON devices."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .compat import BinarySensorDeviceClass
from .const import DOMAIN
from .coordinator import VsonCoordinator
from .devices import CAP_FOOD_LEVEL, CAP_ONLINE, VsonDevice
from .entity import ReefRoleMixin, VsonEntity

_LOGGER = logging.getLogger(__name__)


def _food_shortage(dev: VsonDevice) -> bool | None:
    """Best-effort food-shortage flag for the WP8621 feeder.

    The home payload exposes ``isMaterialRemind`` (low-food reminder) and
    ``isMaterial``. We report a problem when the reminder is active or the
    material flag reads empty.
    """
    remind = dev.value("isMaterialRemind")
    material = dev.value("isMaterial")
    if remind is None and material is None:
        return None
    try:
        if remind is not None and int(remind) == 1:
            return True
        if material is not None and int(material) == 0:
            return True
    except (TypeError, ValueError):
        return None
    return False


@dataclass(frozen=True, kw_only=True)
class VsonBinaryDescription(BinarySensorEntityDescription):
    capability: str = ""
    value_fn: Callable[[VsonDevice], bool | None] | None = None


BINARY_DESCRIPTIONS: tuple[VsonBinaryDescription, ...] = (
    VsonBinaryDescription(
        key="online",
        translation_key="online",
        capability=CAP_ONLINE,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda dev: dev.is_online,
    ),
    VsonBinaryDescription(
        key="food_shortage",
        translation_key="food_shortage",
        capability=CAP_FOOD_LEVEL,
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:food-off",
        value_fn=_food_shortage,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VsonCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for device_id, device in (coordinator.data or {}).items():
        for desc in BINARY_DESCRIPTIONS:
            if device.family.has(desc.capability):
                entities.append(VsonBinarySensor(coordinator, device_id, desc))
    async_add_entities(entities)


class VsonBinarySensor(ReefRoleMixin, VsonEntity, BinarySensorEntity):  # type: ignore[misc]
    """A VSON condition exposed as a binary sensor."""

    def __init__(
        self,
        coordinator: VsonCoordinator,
        device_id: str,
        description: VsonBinaryDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        # The connectivity sensor must stay available to report "offline".
        if self._desc.key == "online":
            return self.coordinator.last_update_success and self._device is not None
        return super().available

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        dev = self._device
        if dev is None or self._desc.value_fn is None:
            return None
        return self._desc.value_fn(dev)
