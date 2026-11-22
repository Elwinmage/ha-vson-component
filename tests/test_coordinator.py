"""Tests for the VSON coordinator."""

from __future__ import annotations

from custom_components.vson_cloud.coordinator import VsonCoordinator
from custom_components.vson_cloud.devices import WP8621A_FAMILY

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
    from custom_components.vson_cloud.devices import VsonDevice

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


# ── Error paths and feed strategies ───────────────────────────────────────────


async def test_client_property(coordinator, mock_client):
    assert coordinator.client is mock_client


async def test_device_list_failure_raises_update_failed(hass, mock_client):
    import pytest
    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.vson_cloud.client import VsonConnectionError

    mock_client.get_devices.side_effect = VsonConnectionError("down")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_skips_devices_without_id_and_tolerates_home_errors(
    hass, mock_client
):
    from custom_components.vson_cloud.client import VsonConnectionError

    from .conftest import MOCK_DEVICE

    mock_client.get_devices.return_value = [{"name": "ghost"}, MOCK_DEVICE]
    mock_client.bley_home.side_effect = VsonConnectionError("timeout")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    data = await coord._async_update_data()
    # The id-less entry is dropped; the feeder is kept without home data.
    assert list(data) == [MOCK_DID]
    assert data[MOCK_DID].home == {}


async def test_update_tolerates_api_errors_on_home(hass, mock_client):
    """A non-zero retCode for one device must not fail the whole poll."""
    from custom_components.vson_cloud.client import VsonApiError

    from .conftest import MOCK_DEVICE, MOCK_GENERIC_DEVICE

    mock_client.get_devices.return_value = [MOCK_DEVICE, MOCK_GENERIC_DEVICE]
    mock_client.bley_home.side_effect = VsonApiError(5, "device busy")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    data = await coord._async_update_data()
    # Both devices survive; only the home payload of the feeder is missing.
    assert sorted(data) == sorted([MOCK_DID, MOCK_GENERIC_DEVICE["id"]])
    assert data[MOCK_DID].home == {}


async def test_feed_now_unknown_device_is_noop(coordinator, mock_client):
    await coordinator.async_feed_now("does-not-exist")
    mock_client.bley_feed_now.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


async def test_feed_now_rotate_mode(coordinator, mock_client, monkeypatch):
    from dataclasses import replace

    from custom_components.vson_cloud import devices
    from custom_components.vson_cloud.const import FEED_MODE_ROTATE_ID
    from custom_components.vson_cloud.devices import WP8621A_FAMILY

    rotate_family = replace(WP8621A_FAMILY, feed_mode=FEED_MODE_ROTATE_ID)
    monkeypatch.setitem(devices._BY_TYPE, "86221", rotate_family)
    await coordinator.async_feed_now(MOCK_DID)
    mock_client.bley_rotate.assert_awaited_once_with(MOCK_DID)
    mock_client.bley_feed_now.assert_not_awaited()
    coordinator.async_request_refresh.assert_awaited_once()


async def test_feed_now_without_mac_logs_and_skips(coordinator, mock_client):
    from custom_components.vson_cloud.devices import VsonDevice

    coordinator.data = {"nomac": VsonDevice(raw={"id": "nomac", "type": "86221"})}
    await coordinator.async_feed_now("nomac")
    mock_client.bley_feed_now.assert_not_awaited()
    mock_client.bley_rotate.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


# ── Session renewal ───────────────────────────────────────────────────────────


async def test_expired_token_triggers_relogin_and_persists_token(hass, mock_client):
    from unittest.mock import MagicMock

    from custom_components.vson_cloud.client import VsonAuthError

    from .conftest import MOCK_DEVICE

    mock_client.get_devices.side_effect = [VsonAuthError("expired"), [MOCK_DEVICE]]
    on_refresh = MagicMock()
    coord = VsonCoordinator(
        hass, mock_client, scan_interval=30, on_token_refresh=on_refresh
    )
    data = await coord._async_update_data()
    assert MOCK_DID in data
    mock_client.authenticate.assert_awaited_once()
    on_refresh.assert_called_once()


async def test_relogin_rejected_raises_config_entry_auth_failed(hass, mock_client):
    import pytest
    from homeassistant.exceptions import ConfigEntryAuthFailed

    from custom_components.vson_cloud.client import VsonAuthError

    mock_client.get_devices.side_effect = VsonAuthError("expired")
    mock_client.authenticate.side_effect = VsonAuthError("wrong password")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


async def test_new_token_rejected_raises_config_entry_auth_failed(hass, mock_client):
    import pytest
    from homeassistant.exceptions import ConfigEntryAuthFailed

    from custom_components.vson_cloud.client import VsonAuthError

    mock_client.get_devices.side_effect = VsonAuthError("expired")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()
    mock_client.authenticate.assert_awaited_once()


async def test_relogin_connection_error_raises_update_failed(hass, mock_client):
    import pytest
    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.vson_cloud.client import (
        VsonAuthError,
        VsonConnectionError,
    )

    mock_client.get_devices.side_effect = VsonAuthError("expired")
    mock_client.authenticate.side_effect = VsonConnectionError("down")
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
