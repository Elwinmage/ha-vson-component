"""Shared pytest fixtures for the VSON tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant import loader
from homeassistant.config_entries import HANDLERS

from custom_components.vson.config_flow import VsonConfigFlow
from custom_components.vson.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.vson.coordinator import VsonCoordinator
from custom_components.vson.devices import VsonDevice

# ── Shared test data ──────────────────────────────────────────────────────────

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "secret"
MOCK_TOKEN = "raw-token-abc123"
MOCK_DID = "a373c1f9a9b0466f9c01f8124cd57f2f"
MOCK_MAC = "AABBCCDDEEFF"

MOCK_DEVICE = {
    "id": MOCK_DID,
    "mac": MOCK_MAC,
    "type": "8621",
    "typeName": "Fish Feeder",
    "name": "Reef Feeder",
    "status": "1",
}

MOCK_GENERIC_DEVICE = {
    "id": "gen-1",
    "mac": "001122334455",
    "type": "9999",
    "typeName": "Mystery Device",
    "name": "Other VSON",
    "status": "0",
}

MOCK_BLEY_HOME = {
    "battery": 80,
    "equipmentState": 1,
    "isMaterial": 1,
    "isMaterialRemind": 0,
    "isPump": 0,
    "version": "1.0.3",
    "time": "2026-11-12 08:00:00",
}

MOCK_CONFIG_ENTRY_DATA = {
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}


# ── Core fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make Home Assistant discover the vson custom component in tests."""
    yield


@pytest.fixture
def domain():
    return DOMAIN


@pytest.fixture
def mock_client():
    """Return a mocked VsonClient."""
    client = MagicMock()
    client.authenticate = AsyncMock(return_value=None)
    client.get_devices = AsyncMock(return_value=[MOCK_DEVICE])
    client.bley_home = AsyncMock(return_value=dict(MOCK_BLEY_HOME))
    client.bley_refresh = AsyncMock(return_value=None)
    client.bley_feed_now = AsyncMock(return_value=None)
    client.bley_set_schedule_enabled = AsyncMock(return_value=None)
    client.token = MOCK_TOKEN
    client.user_id = MOCK_DID
    return client


@pytest.fixture
def device_feeder():
    return VsonDevice(raw=dict(MOCK_DEVICE), home=dict(MOCK_BLEY_HOME))


@pytest.fixture
def device_generic():
    return VsonDevice(raw=dict(MOCK_GENERIC_DEVICE))


@pytest.fixture
def coordinator(hass, mock_client):
    """Coordinator pre-loaded with one online WP8621 feeder."""
    coord = VsonCoordinator(hass, mock_client, scan_interval=30)
    coord.data = {
        MOCK_DID: VsonDevice(raw=dict(MOCK_DEVICE), home=dict(MOCK_BLEY_HOME))
    }
    return coord


@pytest.fixture(autouse=True)
def mock_coordinator_refresh(coordinator):
    """Prevent HA debouncer lingering timers in control tests."""
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_update_listeners = MagicMock()


@pytest.fixture
async def register_config_flow(hass):
    """Make the HA flow engine see the VSON config flow as loaded.

    VsonConfigFlow auto-registers in HANDLERS when its module is imported
    (which conftest already does), so we only mark the config_flow module as
    loaded and must NOT pop the handler on teardown — doing so would remove the
    real registration for the rest of the session and break later tests.
    """
    if HANDLERS.get(DOMAIN) is None:  # defensive: normally set at import
        HANDLERS.register(DOMAIN)(VsonConfigFlow)
    components = hass.data.setdefault(loader.DATA_COMPONENTS, {})
    components[f"{DOMAIN}.config_flow"] = MagicMock()
    yield
    components.pop(f"{DOMAIN}.config_flow", None)
