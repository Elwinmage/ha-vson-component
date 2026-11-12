"""DataUpdateCoordinator for VSON cloud devices."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import VsonClient, VsonConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .devices import VsonDevice

_LOGGER = logging.getLogger(__name__)


class VsonCoordinator(DataUpdateCoordinator[dict[str, VsonDevice]]):
    """Fetch data from all VSON devices at a configurable interval.

    ``data`` is a dict keyed by device_id -> VsonDevice. Each poll fetches the
    account device list, then the realtime "home" payload for every device
    whose family declares one (only the WP8621 feeder today).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: VsonClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        entry_id: str | None = None,
    ) -> None:
        self._client = client
        self.entry_id = entry_id
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @property
    def client(self) -> VsonClient:
        return self._client

    async def _async_update_data(self) -> dict[str, VsonDevice]:
        """Pull fresh data from the VSON cloud."""
        try:
            raw_devices = await self._client.get_devices()
        except VsonConnectionError as exc:
            raise UpdateFailed(f"Failed to fetch device list: {exc}") from exc

        result: dict[str, VsonDevice] = {}
        for raw in raw_devices:
            device = VsonDevice(raw=raw)
            if not device.device_id:
                continue
            family = device.family
            try:
                device.home = await family.fetch_home(self._client, raw)
            except VsonConnectionError as exc:
                _LOGGER.warning(
                    "Could not fetch home data for %s (%s): %s",
                    device.name,
                    device.device_id,
                    exc,
                )
            result[device.device_id] = device
            _LOGGER.debug(
                "Updated %s (%s, family=%s): %s",
                device.name,
                device.device_id,
                family.key,
                device.home or device.raw,
            )

        return result

    async def async_feed_now(self, device_id: str) -> None:
        """Trigger a manual feed on a WP8621, then refresh."""
        device = (self.data or {}).get(device_id)
        if device is None or not device.mac:
            return
        await self._client.bley_feed_now(device.mac)
        await self.async_request_refresh()

    async def async_set_schedule(self, device_id: str, enabled: bool) -> None:
        """Enable/disable scheduled feeding on a WP8621, then refresh."""
        await self._client.bley_set_schedule_enabled(device_id, enabled)
        await self.async_request_refresh()
