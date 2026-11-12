"""Repairs for the VSON integration.

One repair is raised per unknown device ``type``: a VSON device on the account
that no :class:`~.devices.DeviceFamily` maps yet, so it only gets the generic
online/refresh entities. The fix flow shows the device, offers a pre-filled
link to open an issue on the ha-vson-component GitHub repository, and dismisses
the repair once acknowledged.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, GITHUB_REPO, ISSUE_UNKNOWN_DEVICE


def unknown_device_issue_id(type_code: str) -> str:
    """Stable issue id for an unknown device type (one issue per type)."""
    return f"{ISSUE_UNKNOWN_DEVICE}_{type_code}"


def github_issue_url(type_code: str, type_name: str) -> str:
    """Pre-filled 'new issue' URL for an unsupported device type."""
    title = f"Unsupported VSON device type {type_code}"
    body = (
        "A VSON device on my account is not mapped by the integration yet.\n\n"
        f"- type: {type_code}\n"
        f"- typeName: {type_name}\n\n"
        "Please add support for this device family.\n\n"
        "<!-- If you can, paste the raw queryHomePage / query<Family>Homepage "
        "output for this device here. -->\n"
    )
    return (
        f"https://github.com/{GITHUB_REPO}/issues/new"
        f"?title={quote(title)}&body={quote(body)}&labels=new-device"
    )


def async_reconcile_unknown_devices(
    hass: HomeAssistant, unknown: dict[str, str]
) -> None:
    """Create/delete the unknown-device repairs to match the current devices.

    Args:
        unknown: ``{type_code: device_name}`` for every device that fell back
            to the generic family. Types absent from it have their issue
            cleared (the device was removed, or a new release now maps it).
    """
    registry = ir.async_get(hass)
    wanted = {unknown_device_issue_id(code): code for code in unknown}

    # Drop issues for types no longer unknown.
    for issue in list(registry.issues.values()):
        if issue.domain != DOMAIN:
            continue
        if issue.issue_id.startswith(ISSUE_UNKNOWN_DEVICE) and (
            issue.issue_id not in wanted
        ):
            ir.async_delete_issue(hass, DOMAIN, issue.issue_id)

    # Raise one issue per unknown type.
    for type_code, name in unknown.items():
        issue_id = unknown_device_issue_id(type_code)
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_UNKNOWN_DEVICE,
            translation_placeholders={"name": name, "type": type_code},
            learn_more_url=github_issue_url(type_code, name),
            data={"type": type_code, "name": name},
        )


class UnknownDeviceRepairFlow(RepairsFlow):
    """Acknowledge an unknown device after (optionally) opening an issue."""

    def __init__(self, type_code: str, name: str) -> None:
        self._type_code = type_code
        self._name = name

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> Any:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, str] | None = None) -> Any:
        if user_input is None:
            return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "name": self._name,
                    "type": self._type_code,
                    "url": github_issue_url(self._type_code, self._name),
                },
            )
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Return the fix flow for a VSON repair."""
    data = data or {}
    return UnknownDeviceRepairFlow(
        str(data.get("type", "?")), str(data.get("name", ""))
    )
