"""Generic device-family registry for VSON devices.

VSON sells many connected products (feeders, pumps, lights, ...). The cloud
reports each device with a ``type`` code in queryHomePage, and each family is
driven by its own set of ``/api/air/`` endpoints. This module maps a type code
to a :class:`DeviceFamily` that declares:

  - the model label shown in Home Assistant,
  - which capabilities (and therefore which entities) the family exposes,
  - how to fetch the family's realtime "home" payload, if any.

Only the WP8621 auto-feeder is fully mapped today. Every other VSON device
still appears in Home Assistant through the :data:`GENERIC_FAMILY` fallback,
which exposes its online state and a refresh button from the device-list entry
alone — so the integration is useful for the whole brand, and new families are
added here without touching the platforms.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .const import (
    FEED_MODE_FEED_MAC,
    MANUFACTURER,
    TYPE_WP8621,
    TYPE_WP8621_ALT,
    TYPE_WP8621A,
    TYPE_WP8622,
    TYPE_WP8623,
)

if TYPE_CHECKING:
    from .client import VsonClient

_LOGGER = logging.getLogger(__name__)

# A capability flag is just a string; platforms test membership. Keeping them
# as plain strings (not an enum) makes adding a new family a one-line change.
CAP_ONLINE = "online"  # generic: online binary sensor from device "status"
CAP_REFRESH = "refresh"  # generic: force a coordinator refresh
CAP_FEED = "feed"  # feeder: "feed now" button
CAP_SCHEDULE = "schedule"  # feeder: scheduled-feeding switch
CAP_BATTERY = "battery"  # feeder: battery sensor
CAP_FOOD_LEVEL = "food_level"  # feeder: food-shortage binary sensor
CAP_FIRMWARE = "firmware"  # firmware-version diagnostic sensor


async def _fetch_none(_client: VsonClient, _device: dict) -> dict:
    """Family with no rich endpoint: realtime data is the device-list entry."""
    return {}


async def _fetch_bley_home(client: VsonClient, device: dict) -> dict:
    """WP8621: pull the realtime Device8621HomeDataBean by mac."""
    mac = device.get("mac")
    if not mac:
        return {}
    return await client.bley_home(mac)


@dataclass(frozen=True)
class DeviceFamily:
    """Describes one VSON device family and what it exposes to Home Assistant."""

    key: str
    model: str
    type_codes: frozenset[str]
    capabilities: frozenset[str]
    fetch_home: Callable[[VsonClient, dict], Awaitable[dict]] = _fetch_none
    manufacturer: str = MANUFACTURER
    feed_mode: str = ""  # one of const.FEED_MODE_* when CAP_FEED is set

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


_FEEDER_CAPS = frozenset(
    {
        CAP_ONLINE,
        CAP_REFRESH,
        CAP_FEED,
        CAP_SCHEDULE,
        CAP_BATTERY,
        CAP_FOOD_LEVEL,
        CAP_FIRMWARE,
    }
)

# ── Base WP8621 feeder: manual feed via updateBleyFeed(mac) ───────────────────
WP8621_FAMILY = DeviceFamily(
    key="wp8621",
    model="WP8621",
    type_codes=frozenset({TYPE_WP8621, TYPE_WP8621_ALT}),
    capabilities=_FEEDER_CAPS,
    fetch_home=_fetch_bley_home,
    feed_mode=FEED_MODE_FEED_MAC,
)

# ── WP8621A / 8622 / 8623 feeder ──────────────────────────────────────────────
# Manual feed is updateBleyFeed(mac): verified on a real WP8621NK (type 86221),
# it dispenses even while the cloud reports the device offline. The app's
# queryBleyRotateUrl(id) path does NOT dispense here, so feed_mac is used.
WP8621A_FAMILY = DeviceFamily(
    key="wp8621a",
    model="WP8621A",
    type_codes=frozenset({TYPE_WP8621A, TYPE_WP8622, TYPE_WP8623}),
    capabilities=_FEEDER_CAPS,
    fetch_home=_fetch_bley_home,
    feed_mode=FEED_MODE_FEED_MAC,
)

# ── Generic fallback for any other VSON device ────────────────────────────────
# Exposes only what the device-list entry already provides: online state and a
# manual refresh. Enough for a device to show up and be monitored.
GENERIC_FAMILY = DeviceFamily(
    key="generic",
    model="VSON device",
    type_codes=frozenset(),
    capabilities=frozenset({CAP_ONLINE, CAP_REFRESH}),
)

# Registry of fully-mapped families. Add new DeviceFamily entries here.
FAMILIES: tuple[DeviceFamily, ...] = (WP8621_FAMILY, WP8621A_FAMILY)

_BY_TYPE: dict[str, DeviceFamily] = {
    code: fam for fam in FAMILIES for code in fam.type_codes
}


def resolve_family(type_code: Any) -> DeviceFamily:
    """Return the family for a device ``type`` code, or the generic fallback."""
    return _BY_TYPE.get(str(type_code), GENERIC_FAMILY)


@dataclass
class VsonDevice:
    """Parsed state for one device: device-list fields + realtime home data."""

    raw: dict = field(default_factory=dict)
    home: dict = field(default_factory=dict)

    @property
    def device_id(self) -> str:
        return str(self.raw.get("id") or self.raw.get("mac") or "")

    @property
    def mac(self) -> str:
        return str(self.raw.get("mac") or "")

    @property
    def type_code(self) -> str:
        return str(self.raw.get("type") or "")

    @property
    def name(self) -> str:
        return self.raw.get("name") or self.raw.get("typeName") or f"VSON {self.mac}"

    @property
    def family(self) -> DeviceFamily:
        return resolve_family(self.type_code)

    @property
    def is_online(self) -> bool | None:
        """Tri-state online flag.

        For feeders the reliable signal is ``equipmentState`` in the realtime
        home data: 0 = online, non-zero = offline (app handleOnlineStatus). The
        device-list ``onoff`` is unreliable on these models, so it is only a
        fallback for devices without home data. None means unknown. Note that
        availability does not depend on this (see entity.py).
        """
        state = self.home.get("equipmentState")
        if state is not None:
            try:
                return int(state) == 0
            except (TypeError, ValueError):
                pass
        raw = self.raw.get("onoff")
        if raw is None:
            raw = self.raw.get("status")
        if raw is None:
            return None
        text = str(raw).lower()
        if text in ("1", "online", "true", "on"):
            return True
        if text in ("0", "offline", "false", "off"):
            return False
        return None

    def value(self, key: str, default: Any = None) -> Any:
        """Read a realtime home value, falling back to the device-list entry."""
        if key in self.home:
            return self.home[key]
        return self.raw.get(key, default)
