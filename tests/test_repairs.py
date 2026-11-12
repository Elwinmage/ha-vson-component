"""Tests for the unknown-device repair."""

from __future__ import annotations

from homeassistant.helpers import issue_registry as ir

from custom_components.vson.const import DOMAIN
from custom_components.vson.repairs import (
    UnknownDeviceRepairFlow,
    async_create_fix_flow,
    async_reconcile_unknown_devices,
    github_issue_url,
    unknown_device_issue_id,
)


def test_issue_id_and_url():
    assert unknown_device_issue_id("9999") == "unknown_device_9999"
    url = github_issue_url("9999", "Mystery Device")
    assert url.startswith("https://github.com/Elwinmage/ha-vson-component/issues/new")
    assert "9999" in url
    assert "Mystery%20Device" in url


async def test_reconcile_creates_and_clears_issues(hass):
    reg = ir.async_get(hass)

    async_reconcile_unknown_devices(hass, {"9999": "Mystery Device"})
    issue = reg.async_get_issue(DOMAIN, "unknown_device_9999")
    assert issue is not None
    assert issue.translation_placeholders == {"name": "Mystery Device", "type": "9999"}
    assert issue.learn_more_url and "9999" in issue.learn_more_url

    # The device is gone (or now mapped) -> the issue is cleared.
    async_reconcile_unknown_devices(hass, {})
    assert reg.async_get_issue(DOMAIN, "unknown_device_9999") is None


async def test_fix_flow_confirm_dismisses(hass):
    flow = await async_create_fix_flow(
        hass, "unknown_device_9999", {"type": "9999", "name": "Mystery"}
    )
    assert isinstance(flow, UnknownDeviceRepairFlow)
    flow.hass = hass
    form = await flow.async_step_init()
    assert form["type"] == "form"
    assert form["description_placeholders"]["type"] == "9999"
    done = await flow.async_step_confirm({})
    assert done["type"] == "create_entry"


async def test_coordinator_raises_issue_for_generic_device(hass):
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.vson.coordinator import VsonCoordinator

    from .conftest import MOCK_GENERIC_DEVICE

    client = MagicMock()
    client.get_devices = AsyncMock(return_value=[MOCK_GENERIC_DEVICE])
    coord = VsonCoordinator(hass, client, scan_interval=30)
    await coord._async_update_data()

    reg = ir.async_get(hass)
    assert reg.async_get_issue(DOMAIN, "unknown_device_9999") is not None
