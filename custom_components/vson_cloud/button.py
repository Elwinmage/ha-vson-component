"""Button platform for VSON devices: feed now and force refresh."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VsonCoordinator
from .devices import CAP_FEED, CAP_REFRESH
from .entity import ReefRoleMixin, VsonEntity

_LOGGER = logging.getLogger(__name__)

FEED_DESCRIPTION = ButtonEntityDescription(
    key="feed",
    translation_key="feed",
    icon="mdi:fish",
)
REFRESH_DESCRIPTION = ButtonEntityDescription(
    key="refresh",
    translation_key="refresh",
    icon="mdi:refresh",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VsonCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []
    for device_id, device in (coordinator.data or {}).items():
        if device.family.has(CAP_FEED):
            entities.append(VsonFeedButton(coordinator, device_id, FEED_DESCRIPTION))
        if device.family.has(CAP_REFRESH):
            entities.append(
                VsonRefreshButton(coordinator, device_id, REFRESH_DESCRIPTION)
            )
    async_add_entities(entities)


class VsonFeedButton(ReefRoleMixin, VsonEntity, ButtonEntity):  # type: ignore[misc]
    """Dispense one manual portion on a WP8621 feeder."""

    def __init__(
        self,
        coordinator: VsonCoordinator,
        device_id: str,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        _LOGGER.debug("Manual feed requested for %s", self._device_id)
        await self.coordinator.async_feed_now(self._device_id)


class VsonRefreshButton(VsonEntity, ButtonEntity):  # type: ignore[misc]
    """Force an immediate coordinator refresh."""

    def __init__(
        self,
        coordinator: VsonCoordinator,
        device_id: str,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        # Available even when offline, so the user can force a status check.
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        dev = self._device
        if dev is not None and dev.mac and dev.family.has(CAP_FEED):
            # Nudge the device to push fresh data before we re-read it.
            try:
                await self.coordinator.client.bley_refresh(dev.mac)
            except Exception:
                pass
        await self.coordinator.async_request_refresh()
