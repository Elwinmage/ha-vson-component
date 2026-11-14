# pyright: reportMissingImports=false
"""Helpers for the VSON WP8621 fish feeder running on its original BK7231N.

Adding ``vson_feeder:`` to a configuration:

- compiles the C++ helpers and makes them available to lambdas, e.g.
  ``vson_feeder::read_food_sensor()``;
- makes wireless updates work with the stock bootloader of the feeder, by
  building the OTA part of ``firmware.uf2`` in the format that bootloader
  installs (see ``vson_ota.py.script``);
- gives each feeder a distinct, locally-administered MAC derived from its
  ESPHome name, instead of LibreTiny's fixed default (see ``vson_mac.py.script``
  and ``__wrap_cfg_load_mac`` in ``vson_feeder.cpp``).
"""

from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import PLATFORM_BK72XX
from esphome.core import CORE
from esphome.helpers import copy_file_if_changed

CONF_STOCK_BOOTLOADER_OTA = "stock_bootloader_ota"
CONF_UNIQUE_MAC = "unique_mac"

OTA_SCRIPT = "vson_ota.py"
MAC_SCRIPT = "vson_mac.py"

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
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

    # PlatformIO extra scripts, run after LibreTiny's builder is set up. Collect
    # them and register them in one option (a second call would overwrite it).
    scripts = []
    if config[CONF_STOCK_BOOTLOADER_OTA]:
        scripts.append(OTA_SCRIPT)
    if config[CONF_UNIQUE_MAC]:
        scripts.append(MAC_SCRIPT)

    for script in scripts:
        copy_file_if_changed(
            Path(__file__).parent / f"{script}.script",
            CORE.relative_build_path(script),
        )
    if scripts:
        cg.add_platformio_option(
            "extra_scripts", [f"post:{script}" for script in scripts]
        )
