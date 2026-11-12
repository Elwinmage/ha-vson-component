"""Integration setup/unload tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vson.const import DOMAIN

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DID


async def test_setup_and_unload_entry(hass, mock_client):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    with patch("custom_components.vson.VsonClient", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert MOCK_DID in coordinator.data

    # Feeder entities created across platforms.
    assert hass.states.get("sensor.reef_feeder_battery") is not None
    assert hass.states.get("button.reef_feeder_feed_now") is not None
    assert hass.states.get("binary_sensor.reef_feeder_online") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_setup_auth_failure(hass):
    from custom_components.vson.client import VsonAuthError

    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    failing = AsyncMock()
    failing.authenticate = AsyncMock(side_effect=VsonAuthError("bad"))
    with patch("custom_components.vson.VsonClient", return_value=failing):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state.recoverable
