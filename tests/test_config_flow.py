"""Tests for the VSON config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vson_cloud.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_PASSWORD, MOCK_USERNAME


async def test_user_flow_success(hass, register_config_flow):
    with patch(
        "custom_components.vson_cloud.config_flow._validate",
        return_value=("RAWTOKEN", None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USERNAME] == MOCK_USERNAME


async def test_user_flow_invalid_auth(hass, register_config_flow):
    with patch(
        "custom_components.vson_cloud.config_flow._validate",
        return_value=(None, "invalid_auth"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "wrong"},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_options_flow_updates_interval(hass, register_config_flow):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload",
        return_value=True,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 120}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_SCAN_INTERVAL] == 120


async def test_reauth_flow(hass, register_config_flow):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    with (
        patch(
            "custom_components.vson_cloud.config_flow._validate",
            return_value=("NEWTOKEN", None),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_reload",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "newpass"}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "newpass"


# ── Credential validation ─────────────────────────────────────────────────────


async def test_validate_maps_errors(hass):
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.vson_cloud.client import (
        VsonAuthError,
        VsonConnectionError,
    )
    from custom_components.vson_cloud.config_flow import _validate

    cases = [
        (None, ("TOKEN", None)),
        (VsonAuthError("bad"), (None, "invalid_auth")),
        (VsonConnectionError("down"), (None, "cannot_connect")),
        (RuntimeError("??"), (None, "unknown")),
    ]
    for side_effect, expected in cases:
        client = MagicMock(token="TOKEN")
        client.authenticate = AsyncMock(side_effect=side_effect)
        with patch(
            "custom_components.vson_cloud.config_flow.VsonClient",
            return_value=client,
        ):
            assert await _validate(hass, MOCK_USERNAME, MOCK_PASSWORD) == expected


async def test_reauth_flow_error(hass, register_config_flow):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(
        "custom_components.vson_cloud.config_flow._validate",
        return_value=(None, "cannot_connect"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "newpass"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"
    assert entry.data[CONF_PASSWORD] == MOCK_PASSWORD


async def test_reconfigure_flow(hass, register_config_flow):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_ENTRY_DATA, unique_id="test@example.com"
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.vson_cloud.config_flow._validate",
        return_value=(None, "invalid_auth"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "wrong"},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"

    with (
        patch(
            "custom_components.vson_cloud.config_flow._validate",
            return_value=("NEWTOKEN", None),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_reload",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: " other@example.com ",
                CONF_PASSWORD: "newpass",
                CONF_SCAN_INTERVAL: 90,
            },
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_USERNAME] == "other@example.com"
    assert entry.data[CONF_SCAN_INTERVAL] == 90
