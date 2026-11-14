"""Helpers for the VSON WP8621 fish feeder running on its original BK7231N.

Adding ``vson_feeder:`` to a configuration:

- compiles the C++ helpers and makes them available to lambdas, e.g.
  ``vson_feeder::read_food_sensor()``;
- makes wireless updates work with the stock bootloader of the feeder, by
  building the OTA part of ``firmware.uf2`` in the format that bootloader
  installs (see ``vson_ota.py.script``).
"""

# pyright: reportMissingImports=false

from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import PLATFORM_BK72XX
from esphome.core import CORE
from esphome.helpers import copy_file_if_changed

CONF_STOCK_BOOTLOADER_OTA = "stock_bootloader_ota"

OTA_SCRIPT = "vson_ota.py"

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            # Set to false to get LibreTiny's standard OTA image back, e.g. if
            # the stock bootloader has been replaced by a Beken/Tuya one.
            cv.Optional(CONF_STOCK_BOOTLOADER_OTA, default=True): cv.boolean,
        }
    ),
    cv.only_on(PLATFORM_BK72XX),
)


async def to_code(config):
    # Make the helpers visible from the lambdas of the generated main.cpp
    cg.add_global(
        cg.RawStatement('#include "esphome/components/vson_feeder/vson_feeder.h"')
    )

    if config[CONF_STOCK_BOOTLOADER_OTA]:
        # PlatformIO extra script, run after LibreTiny's builder is set up
        copy_file_if_changed(
            Path(__file__).parent / f"{OTA_SCRIPT}.script",
            CORE.relative_build_path(OTA_SCRIPT),
        )
        cg.add_platformio_option("extra_scripts", [f"post:{OTA_SCRIPT}"])
