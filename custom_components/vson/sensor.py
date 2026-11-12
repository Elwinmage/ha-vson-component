"""Sensor platform for VSON devices."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VsonCoordinator
from .devices import CAP_BATTERY, CAP_FIRMWARE, VsonDevice
from .entity import ReefRoleMixin, VsonEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VsonSensorDescription(SensorEntityDescription):
    """A sensor bound to a device-home attribute and a required capability."""

    capability: str = ""
    attr: str = ""
    value_fn: Callable[[VsonDevice], object] | None = None


SENSOR_DESCRIPTIONS: tuple[VsonSensorDescription, ...] = (
    VsonSensorDescription(
        key="battery",
        translation_key="battery",
        capability=CAP_BATTERY,
        attr="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VsonSensorDescription(
        key="firmware",
        translation_key="firmware",
        capability=CAP_FIRMWARE,
        attr="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VsonCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for device_id, device in (coordinator.data or {}).items():
        for desc in SENSOR_DESCRIPTIONS:
            if device.family.has(desc.capability):
                entities.append(VsonSensor(coordinator, device_id, desc))
    async_add_entities(entities)


class VsonSensor(ReefRoleMixin, VsonEntity, SensorEntity):  # type: ignore[misc]
    """A VSON attribute exposed as a sensor."""

    def __init__(
        self,
        coordinator: VsonCoordinator,
        device_id: str,
        description: VsonSensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def native_value(self):  # type: ignore[override]
        dev = self._device
        if dev is None:
            return None
        if self._desc.value_fn is not None:
            return self._desc.value_fn(dev)
        return dev.value(self._desc.attr)
