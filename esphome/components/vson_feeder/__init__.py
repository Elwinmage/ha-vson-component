# pyright: reportMissingImports=false
"""Helpers for the VSON WP8621 fish feeder running on its original BK7231N.

Adding ``vson_feeder:`` to a configuration:

- compiles the C++ helpers and makes them available to lambdas, e.g.
  ``vson_feeder::read_food_sensor()``;
- makes wireless updates work with the stock bootloader of the feeder, by
  building the OTA part of ``firmware.uf2`` in the format that bootloader
  installs (see ``vson_ota.py.script``);
- gives each feeder a distinct, locally-administered MAC derived from its
  ESPHome name, instead of LibreTiny's fixed default. This is done by wrapping
  ``wifi_get_mac_address()`` at link time (``-Wl,-wrap,...``); see
  ``__wrap_wifi_get_mac_address`` in ``vson_feeder.cpp``;
- logs a short diagnostic banner at boot (component revision, whether the MAC
  hook was actually linked in, and the effective STA MAC) so a single boot log
  tells whether a new build really took effect.
"""

from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID, PLATFORM_BK72XX
from esphome.core import CORE
from esphome.helpers import copy_file_if_changed

CONF_STOCK_BOOTLOADER_OTA = "stock_bootloader_ota"
CONF_UNIQUE_MAC = "unique_mac"

OTA_SCRIPT = "vson_ota.py"

# Link-time hook that replaces the module's fixed default MAC with a per-device
# one. It must land in the final link's LINKFLAGS; adding it as a build flag is
# the canonical ESPHome path (PlatformIO routes -Wl,* build flags to LINKFLAGS,
# and LibreTiny's link step honours them, as it uses -Wl,-wrap itself).
MAC_WRAP_FLAG = "-Wl,-wrap,wifi_get_mac_address"

vson_feeder_ns = cg.esphome_ns.namespace("vson_feeder")
VsonFeeder = vson_feeder_ns.class_("VsonFeeder", cg.Component)

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(VsonFeeder),
            # Set to false to get LibreTiny's standard OTA image back, e.g. if
            # the stock bootloader has been replaced by a Beken/Tuya one.
            cv.Optional(CONF_STOCK_BOOTLOADER_OTA, default=True): cv.boolean,
            # Set to false to keep LibreTiny's default MAC (e.g. if you run a
            # single feeder, or set the MAC by other means).
            cv.Optional(CONF_UNIQUE_MAC, default=True): cv.boolean,
        }
    ),
    cv.only_on(PLATFORM_BK72XX),
)


async def to_code(config):
    # Make the helpers visible from the lambdas of the generated main.cpp
    cg.add_global(
        cg.RawStatement('#include "esphome/components/vson_feeder/vson_feeder.h"')
    )

    # Instantiate the component so its dump_config() prints the diagnostic banner.
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Per-device MAC: add the link-time wrap flag (canonical, reaches the link).
    if config[CONF_UNIQUE_MAC]:
        cg.add_build_flag(MAC_WRAP_FLAG)
        cg.add_define("VSON_UNIQUE_MAC")

    # Stock-bootloader OTA image is produced by a PlatformIO post extra script.
    if config[CONF_STOCK_BOOTLOADER_OTA]:
        copy_file_if_changed(
            Path(__file__).parent / f"{OTA_SCRIPT}.script",
            CORE.relative_build_path(OTA_SCRIPT),
        )
        cg.add_platformio_option("extra_scripts", [f"post:{OTA_SCRIPT}"])
