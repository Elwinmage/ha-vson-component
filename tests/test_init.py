"""Integration setup/unload tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vson_cloud.const import DOMAIN

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DID


async def test_setup_and_unload_entry(hass, mock_client):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    with patch("custom_components.vson_cloud.VsonClient", return_value=mock_client):
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
    from custom_components.vson_cloud.client import VsonAuthError

    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)

    failing = AsyncMock()
    failing.authenticate = AsyncMock(side_effect=VsonAuthError("bad"))
    with patch("custom_components.vson_cloud.VsonClient", return_value=failing):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state.recoverable


def _entry(hass, **data):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**MOCK_CONFIG_ENTRY_DATA, **data},
        unique_id="test@example.com",
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_connection_failure_is_not_ready(hass):
    from homeassistant.config_entries import ConfigEntryState

    from custom_components.vson_cloud.client import VsonConnectionError

    entry = _entry(hass)
    failing = AsyncMock()
    failing.authenticate = AsyncMock(side_effect=VsonConnectionError("down"))
    with patch("custom_components.vson_cloud.VsonClient", return_value=failing):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_keeps_unchanged_token_and_prunes_stale_devices(hass, mock_client):
    from homeassistant.helpers import device_registry as dr

    from custom_components.vson_cloud import async_remove_config_entry_device
    from custom_components.vson_cloud.const import CONF_TOKEN

    from .conftest import MOCK_TOKEN

    entry = _entry(hass, **{CONF_TOKEN: MOCK_TOKEN})
    dev_reg = dr.async_get(hass)
    stale = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "gone")}, name="Old"
    )
    foreign = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "x")}, name="Foreign"
    )
    known = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, MOCK_DID)}
    )

    with (
        patch("custom_components.vson_cloud.VsonClient", return_value=mock_client),
        patch.object(
            hass.config_entries,
            "async_update_entry",
            wraps=hass.config_entries.async_update_entry,
        ) as update_entry,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    # Token already stored: the entry is not rewritten.
    update_entry.assert_not_called()

    # The stale device is detached; the others are kept.
    assert dev_reg.async_get(stale.id) is None
    assert dev_reg.async_get(foreign.id) is not None
    assert dev_reg.async_get(known.id) is not None

    # UI deletion is only allowed for devices the account no longer reports.
    assert not await async_remove_config_entry_device(hass, entry, known)
    assert await async_remove_config_entry_device(hass, entry, foreign)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    # Without a coordinator, every device may be removed.
    assert await async_remove_config_entry_device(hass, entry, known)


async def test_setup_with_empty_account_keeps_registry(hass, mock_client):
    from homeassistant.helpers import device_registry as dr

    entry = _entry(hass)
    dev_reg = dr.async_get(hass)
    old = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "gone")}
    )
    mock_client.get_devices.return_value = []
    with patch("custom_components.vson_cloud.VsonClient", return_value=mock_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    # A transient empty answer must not wipe the registry.
    assert dev_reg.async_get(old.id) is not None
