#pragma once

// Helpers for the VSON WP8621 feeder running on its original BK7231N.

namespace esphome {
namespace vson_feeder {

// Voltage (in volts) of the food level phototransistor wired to P22, averaged
// over a few samples. Returns NAN when the ADC is busy or does not answer.
// The IR emitter (P23) must be switched on before calling this.
float read_food_sensor();

}  // namespace vson_feeder
}  // namespace esphome
