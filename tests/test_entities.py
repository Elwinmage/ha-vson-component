"""Tests for the VSON platform entities."""

from __future__ import annotations

from custom_components.vson.binary_sensor import (
    BINARY_DESCRIPTIONS,
    VsonBinarySensor,
)
from custom_components.vson.button import FEED_DESCRIPTION, VsonFeedButton
from custom_components.vson.devices import VsonDevice
from custom_components.vson.sensor import SENSOR_DESCRIPTIONS, VsonSensor
from custom_components.vson.switch import VsonScheduleSwitch

from .conftest import MOCK_DID


def _desc(descriptions, key):
    return next(d for d in descriptions if d.key == key)


def test_battery_sensor_value(coordinator):
    sensor = VsonSensor(coordinator, MOCK_DID, _desc(SENSOR_DESCRIPTIONS, "battery"))
    assert sensor.native_value == 80
    assert sensor.unique_id == f"{MOCK_DID}_battery"


def test_firmware_sensor_value(coordinator):
    sensor = VsonSensor(coordinator, MOCK_DID, _desc(SENSOR_DESCRIPTIONS, "firmware"))
    assert sensor.native_value == "1.0.3"


async def test_battery_sensor_skipped_when_absent(hass, mock_client):
    """A mains-powered feeder (no 'battery' field) gets no battery sensor."""
    from unittest.mock import AsyncMock

    from custom_components.vson import sensor as sensor_platform
    from custom_components.vson.coordinator import VsonCoordinator
    from custom_components.vson.devices import VsonDevice

    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    coord.data = {
        MOCK_DID: VsonDevice(
            raw={"id": MOCK_DID, "mac": "x", "type": "86221", "onoff": "1"},
            home={"version": "WP8621NK_04", "isMaterial": "1"},  # no battery
        )
    }
    hass.data["vson"] = {"e": coord}
    entry = AsyncMock(entry_id="e")
    added: list = []
    await sensor_platform.async_setup_entry(hass, entry, lambda es: added.extend(es))
    keys = {e.entity_description.key for e in added}
    assert "battery" not in keys
    assert "firmware" in keys


def test_online_binary_sensor(coordinator):
    bs = VsonBinarySensor(coordinator, MOCK_DID, _desc(BINARY_DESCRIPTIONS, "online"))
    assert bs.is_on is True
    # The connectivity sensor publishes the reef_role attribute for the card.
    assert bs.extra_state_attributes["reef_role"] == "online"


def test_food_shortage_logic(coordinator):
    bs = VsonBinarySensor(
        coordinator, MOCK_DID, _desc(BINARY_DESCRIPTIONS, "food_shortage")
    )
    # Default mock: isMaterial=0 → food present, no shortage.
    assert bs.is_on is False
    # isMaterial == 1 means shortage.
    coordinator.data[MOCK_DID] = VsonDevice(
        raw=coordinator.data[MOCK_DID].raw, home={"isMaterial": 1}
    )
    assert bs.is_on is True


async def test_feed_button_presses_coordinator(coordinator, mock_client):
    button = VsonFeedButton(coordinator, MOCK_DID, FEED_DESCRIPTION)
    await button.async_press()
    # WP8621A feeds via updateBleyFeed(mac).
    mock_client.bley_feed_now.assert_awaited_once_with("AABBCCDDEEFF")


async def test_schedule_switch_optimistic(coordinator, mock_client):
    from unittest.mock import MagicMock

    sw = VsonScheduleSwitch(coordinator, MOCK_DID)
    assert sw.is_on is None
    # Entity is not attached to a platform here; stub the state write.
    sw.async_write_ha_state = MagicMock()
    await sw.async_turn_on()
    assert sw.is_on is True
    mock_client.bley_set_schedule_enabled.assert_awaited_with(MOCK_DID, True)
    await sw.async_turn_off()
    assert sw.is_on is False
