"""Tests for the generic device-family registry."""

from __future__ import annotations

from custom_components.vson.const import FEED_MODE_FEED_MAC
from custom_components.vson.devices import (
    CAP_FEED,
    CAP_ONLINE,
    GENERIC_FAMILY,
    WP8621_FAMILY,
    WP8621A_FAMILY,
    VsonDevice,
    resolve_family,
)


def test_resolve_known_feeder():
    assert resolve_family("8621") is WP8621_FAMILY
    assert resolve_family("86211") is WP8621_FAMILY
    assert resolve_family("86221") is WP8621A_FAMILY
    assert resolve_family("8622") is WP8621A_FAMILY


def test_feeders_use_feed_mac():
    assert WP8621_FAMILY.feed_mode == FEED_MODE_FEED_MAC
    assert WP8621A_FAMILY.feed_mode == FEED_MODE_FEED_MAC


def test_resolve_unknown_falls_back_to_generic():
    assert resolve_family("9999") is GENERIC_FAMILY
    assert resolve_family(None) is GENERIC_FAMILY


def test_family_capabilities():
    assert WP8621A_FAMILY.has(CAP_FEED)
    assert WP8621A_FAMILY.has(CAP_ONLINE)
    assert not GENERIC_FAMILY.has(CAP_FEED)
    assert GENERIC_FAMILY.has(CAP_ONLINE)


def test_device_identity(device_feeder):
    assert device_feeder.device_id == "a373c1f9a9b0466f9c01f8124cd57f2f"
    assert device_feeder.mac == "AABBCCDDEEFF"
    assert device_feeder.name == "Reef Feeder"
    assert device_feeder.family is WP8621A_FAMILY


def test_device_online_prefers_equipment_state():
    # equipmentState from home data wins: 0 = online, non-zero = offline.
    assert VsonDevice(raw={}, home={"equipmentState": "0"}).is_online is True
    assert VsonDevice(raw={}, home={"equipmentState": "2"}).is_online is False
    # onoff/status is only a fallback when there is no home data.
    assert VsonDevice(raw={"onoff": "1"}).is_online is True
    assert VsonDevice(raw={"onoff": "0"}).is_online is False
    assert VsonDevice(raw={}).is_online is None


def test_value_prefers_home_over_raw():
    dev = VsonDevice(raw={"battery": 10}, home={"battery": 88})
    assert dev.value("battery") == 88
    assert dev.value("missing", "x") == "x"
