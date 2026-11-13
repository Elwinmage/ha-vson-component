"""Helpers for the VSON WP8621 fish feeder running on its original BK7231N.

Adding ``vson_feeder:`` to a configuration compiles the C++ helpers and makes
them available to lambdas, e.g. ``vson_feeder::read_food_sensor()``.
"""
# pyright: reportMissingImports=false
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import PLATFORM_BK72XX

CONFIG_SCHEMA = cv.All(cv.Schema({}), cv.only_on(PLATFORM_BK72XX))


async def to_code(config):
    # Make the helpers visible from the lambdas of the generated main.cpp
    cg.add_global(
        cg.RawStatement('#include "esphome/components/vson_feeder/vson_feeder.h"')
    )
