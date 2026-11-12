"""Tests for the generic device-family registry."""

from __future__ import annotations

from custom_components.vson.devices import (
    CAP_FEED,
    CAP_ONLINE,
    GENERIC_FAMILY,
    WP8621_FAMILY,
    VsonDevice,
    resolve_family,
)


def test_resolve_known_feeder():
    assert resolve_family("8621") is WP8621_FAMILY
    assert resolve_family("86211") is WP8621_FAMILY


def test_resolve_unknown_falls_back_to_generic():
    assert resolve_family("9999") is GENERIC_FAMILY
    assert resolve_family(None) is GENERIC_FAMILY


def test_family_capabilities():
    assert WP8621_FAMILY.has(CAP_FEED)
    assert WP8621_FAMILY.has(CAP_ONLINE)
    assert not GENERIC_FAMILY.has(CAP_FEED)
    assert GENERIC_FAMILY.has(CAP_ONLINE)


def test_device_identity(device_feeder):
    assert device_feeder.device_id == "a373c1f9a9b0466f9c01f8124cd57f2f"
    assert device_feeder.mac == "AABBCCDDEEFF"
    assert device_feeder.name == "Reef Feeder"
    assert device_feeder.family is WP8621_FAMILY


def test_device_online_tristate():
    assert VsonDevice(raw={"status": "1"}).is_online is True
    assert VsonDevice(raw={"status": "0"}).is_online is False
    assert VsonDevice(raw={}).is_online is None
    assert VsonDevice(raw={"status": "online"}).is_online is True


def test_value_prefers_home_over_raw():
    dev = VsonDevice(raw={"battery": 10}, home={"battery": 88})
    assert dev.value("battery") == 88
    assert dev.value("missing", "x") == "x"
