"""Switch platform for VSON devices: scheduled feeding."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VsonCoordinator
from .devices import CAP_SCHEDULE
from .entity import ReefRoleMixin, VsonEntity

_LOGGER = logging.getLogger(__name__)

SCHEDULE_DESCRIPTION = SwitchEntityDescription(
    key="schedule",
    translation_key="schedule",
    icon="mdi:calendar-clock",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VsonCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    for device_id, device in (coordinator.data or {}).items():
        if device.family.has(CAP_SCHEDULE):
            entities.append(VsonScheduleSwitch(coordinator, device_id))
    async_add_entities(entities)


class VsonScheduleSwitch(ReefRoleMixin, VsonEntity, SwitchEntity):  # type: ignore[misc]
    """Enable or disable a WP8621's scheduled feeding.

    The home payload does not report the schedule-enabled flag, so the switch
    is optimistic (assumed state): toggling it sends the command and remembers
    the chosen state until the entity is reloaded.
    """

    _attr_assumed_state = True

    def __init__(self, coordinator: VsonCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, SCHEDULE_DESCRIPTION.key)
        self.entity_description = SCHEDULE_DESCRIPTION
        self._attr_is_on: bool | None = None

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule(self._device_id, True)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule(self._device_id, False)
        self._attr_is_on = False
        self.async_write_ha_state()
