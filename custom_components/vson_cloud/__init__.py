"""The VSON integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import VsonAuthError, VsonClient, VsonConnectionError
from .const import (
    CONF_ACCOUNT_TYPE,
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import VsonCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    "binary_sensor",
    "button",
    "sensor",
    "switch",
]


def _device_ids(device: dr.DeviceEntry) -> set[str]:
    """VSON device ids carried by a device registry entry."""
    return {ident[1] for ident in device.identifiers if ident[0] == DOMAIN}


@callback
def _async_remove_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, known_ids: set[str]
) -> int:
    """Detach devices the account no longer reports.

    A transient empty answer must not wipe the registry (and its entity
    customisations), so an empty ``known_ids`` is never acted upon.
    """
    if not known_ids:
        return 0
    dev_reg = dr.async_get(hass)
    removed = 0
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        ids = _device_ids(device)
        if not ids or ids & known_ids:
            continue
        _LOGGER.info(
            "[VSON] Removing stale device '%s' (%s): no longer on the account",
            device.name,
            ", ".join(sorted(ids)),
        )
        dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
        removed += 1
    return removed


def _persist_token(hass: HomeAssistant, entry: ConfigEntry, client: VsonClient) -> None:
    """Store the session token in the (HA-encrypted) config entry."""
    if not client.token or entry.data.get(CONF_TOKEN) == client.token:
        return
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_TOKEN: client.token}
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VSON from a config entry."""
    interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    session = async_get_clientsession(hass)

    client = VsonClient(
        session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        account_type=entry.data.get(CONF_ACCOUNT_TYPE),
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        token=entry.data.get(CONF_TOKEN),
        lang=hass.config.language or "en",
    )

    try:
        await client.authenticate()
    except VsonAuthError as exc:
        _LOGGER.error(
            "Authentication failed for %s: %s", entry.data[CONF_USERNAME], exc
        )
        raise ConfigEntryAuthFailed from exc
    except VsonConnectionError as exc:
        _LOGGER.error("Cannot connect to the VSON cloud: %s", exc)
        raise ConfigEntryNotReady from exc

    _persist_token(hass, entry, client)

    coordinator = VsonCoordinator(
        hass, client, scan_interval=interval, entry_id=entry.entry_id
    )
    await coordinator.async_config_entry_first_refresh()

    if coordinator.data:
        _LOGGER.info(
            "[VSON] %d device(s) for '%s' | interval=%ds",
            len(coordinator.data),
            entry.data[CONF_USERNAME],
            interval,
        )
        for dev_id, dev in coordinator.data.items():
            _LOGGER.info(
                "  • %-28s | id=%-24s | type=%-8s | family=%s",
                dev.name,
                dev_id,
                dev.type_code,
                dev.family.key,
            )

    _async_remove_stale_devices(hass, entry, set(coordinator.data or {}))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting a device from the UI once the account no longer has it."""
    coordinator: VsonCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    known = set(coordinator.data or {}) if coordinator else set()
    return not (_device_ids(device) & known)
