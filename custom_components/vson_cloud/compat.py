"""Imports whose home moved between Home Assistant releases.

Home Assistant 2026.10 replaced voluptuous with probatio (same API) and moved
each platform's entity enums to a ``const`` module. Everything is resolved
here, once, so the rest of the integration imports from a single place
whatever the installed version:

    from .compat import BinarySensorDeviceClass, vol
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import probatio as vol
    from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
else:
    try:
        import probatio as vol
    except ImportError:  # pragma: no cover - Home Assistant without probatio
        import voluptuous as vol

    try:
        from homeassistant.components.binary_sensor.const import (
            BinarySensorDeviceClass,
        )
    except ImportError:  # pragma: no cover - Home Assistant < 2026.10
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

__all__ = ["BinarySensorDeviceClass", "vol"]
