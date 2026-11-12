"""Tests for the VSON coordinator."""

from __future__ import annotations

from custom_components.vson.coordinator import VsonCoordinator
from custom_components.vson.devices import WP8621A_FAMILY

from .conftest import MOCK_DID


async def test_update_builds_devices_with_home(hass, mock_client):
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    data = await coord._async_update_data()
    assert MOCK_DID in data
    dev = data[MOCK_DID]
    assert dev.family is WP8621A_FAMILY
    assert dev.value("battery") == 80


async def test_feed_now_uses_feed_mac_for_wp8621a(coordinator, mock_client):
    # WP8621A (type 86221) feeds via updateBleyFeed(mac) — verified on hardware.
    await coordinator.async_feed_now(MOCK_DID)
    mock_client.bley_feed_now.assert_awaited_once_with("AABBCCDDEEFF")
    mock_client.bley_rotate.assert_not_awaited()


async def test_feed_now_uses_feed_mac_for_base_wp8621(hass, mock_client):
    from custom_components.vson.devices import VsonDevice

    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    coord.async_request_refresh = __import__(
        "unittest.mock", fromlist=["AsyncMock"]
    ).AsyncMock()
    # A base WP8621 (type 8621) feeds by mac.
    coord.data = {
        "base-1": VsonDevice(raw={"id": "base-1", "mac": "FF:EE", "type": "8621"})
    }
    await coord.async_feed_now("base-1")
    mock_client.bley_feed_now.assert_awaited_once_with("FF:EE")


async def test_set_schedule_calls_client(coordinator, mock_client):
    await coordinator.async_set_schedule(MOCK_DID, True)
    mock_client.bley_set_schedule_enabled.assert_awaited_once_with(MOCK_DID, True)


async def test_generic_device_has_no_home(hass):
    from unittest.mock import AsyncMock, MagicMock

    from .conftest import MOCK_GENERIC_DEVICE

    client = MagicMock()
    client.get_devices = AsyncMock(return_value=[MOCK_GENERIC_DEVICE])
    coord = VsonCoordinator(hass, client, scan_interval=30)
    data = await coord._async_update_data()
    dev = data["gen-1"]
    assert dev.family.key == "generic"
    assert dev.home == {}
