"""Tests for the VSON platform entities."""

from __future__ import annotations

from custom_components.vson_cloud.binary_sensor import (
    BINARY_DESCRIPTIONS,
    VsonBinarySensor,
)
from custom_components.vson_cloud.button import FEED_DESCRIPTION, VsonFeedButton
from custom_components.vson_cloud.devices import VsonDevice
from custom_components.vson_cloud.sensor import SENSOR_DESCRIPTIONS, VsonSensor
from custom_components.vson_cloud.switch import VsonScheduleSwitch

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

    from custom_components.vson_cloud import sensor as sensor_platform
    from custom_components.vson_cloud.coordinator import VsonCoordinator
    from custom_components.vson_cloud.devices import VsonDevice

    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    coord.data = {
        MOCK_DID: VsonDevice(
            raw={"id": MOCK_DID, "mac": "x", "type": "86221", "onoff": "1"},
            home={"version": "WP8621NK_04", "isMaterial": "1"},  # no battery
        )
    }
    hass.data["vson_cloud"] = {"e": coord}
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


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_food_shortage_unknown_values(coordinator):
    bs = VsonBinarySensor(
        coordinator, MOCK_DID, _desc(BINARY_DESCRIPTIONS, "food_shortage")
    )
    raw = coordinator.data[MOCK_DID].raw
    coordinator.data[MOCK_DID] = VsonDevice(raw=raw, home={"battery": 1})
    assert bs.is_on is None
    coordinator.data[MOCK_DID] = VsonDevice(raw=raw, home={"isMaterial": "n/a"})
    assert bs.is_on is None


def test_entities_without_device(coordinator):
    coordinator.data = {}
    bs = VsonBinarySensor(coordinator, MOCK_DID, _desc(BINARY_DESCRIPTIONS, "online"))
    assert bs.is_on is None
    assert bs.available is False
    sensor = VsonSensor(coordinator, MOCK_DID, _desc(SENSOR_DESCRIPTIONS, "battery"))
    assert sensor.native_value is None
    assert sensor._value("battery", "dflt") == "dflt"


def test_food_shortage_availability_follows_base(coordinator):
    bs = VsonBinarySensor(
        coordinator, MOCK_DID, _desc(BINARY_DESCRIPTIONS, "food_shortage")
    )
    assert bs.available is True


def test_sensor_value_fn_and_value_helper(coordinator):
    from custom_components.vson_cloud.sensor import VsonSensorDescription

    desc = VsonSensorDescription(key="custom", value_fn=lambda dev: dev.mac)
    sensor = VsonSensor(coordinator, MOCK_DID, desc)
    assert sensor.native_value == "AABBCCDDEEFF"
    assert sensor._value("battery") == 80


def test_reef_role_mixin_without_translation_key():
    from custom_components.vson_cloud.entity import ReefRoleMixin

    class _Plain(ReefRoleMixin):
        translation_key = None

    plain = _Plain()
    assert plain.extra_state_attributes is None
    plain._attr_extra_state_attributes = {"a": 1}
    assert plain.extra_state_attributes == {"a": 1}


def test_device_info_without_data(coordinator):
    from custom_components.vson_cloud.entity import build_device_info

    coordinator.data = None
    info = build_device_info(coordinator, "unknown")
    assert info["name"] == "unknown"
    assert info["model"] == "VSON device"


async def test_refresh_button_nudges_feeder(coordinator, mock_client):
    from custom_components.vson_cloud.button import (
        REFRESH_DESCRIPTION,
        VsonRefreshButton,
    )

    mock_client.bley_refresh.side_effect = RuntimeError("cloud hiccup")
    button = VsonRefreshButton(coordinator, MOCK_DID, REFRESH_DESCRIPTION)
    assert button.available is True
    # A failing nudge must not prevent the coordinator refresh.
    await button.async_press()
    mock_client.bley_refresh.assert_awaited_once_with("AABBCCDDEEFF")
    coordinator.async_request_refresh.assert_awaited_once()


async def test_refresh_button_generic_device(coordinator, mock_client):
    from custom_components.vson_cloud.button import (
        REFRESH_DESCRIPTION,
        VsonRefreshButton,
    )

    from .conftest import MOCK_GENERIC_DEVICE

    coordinator.data = {"gen-1": VsonDevice(raw=dict(MOCK_GENERIC_DEVICE))}
    button = VsonRefreshButton(coordinator, "gen-1", REFRESH_DESCRIPTION)
    await button.async_press()
    mock_client.bley_refresh.assert_not_awaited()
    coordinator.async_request_refresh.assert_awaited_once()


async def test_platforms_skip_unsupported_capabilities(hass, coordinator):
    """A generic device only gets the online sensor and the refresh button."""
    from unittest.mock import MagicMock

    from custom_components.vson_cloud import binary_sensor, button, sensor, switch

    from .conftest import MOCK_GENERIC_DEVICE

    coordinator.data = {"gen-1": VsonDevice(raw=dict(MOCK_GENERIC_DEVICE))}
    hass.data["vson_cloud"] = {"e": coordinator}
    entry = MagicMock(entry_id="e")
    added: list = []
    for platform in (binary_sensor, button, sensor, switch):
        await platform.async_setup_entry(hass, entry, added.extend)
    assert sorted(e.entity_description.key for e in added) == ["online", "refresh"]
