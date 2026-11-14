#pragma once

// Helpers for the VSON WP8621 feeder running on its original BK7231N.

#include <stdint.h>
#include "esphome/core/component.h"

namespace esphome {
namespace vson_feeder {

// Bumped on every delivery so the boot log shows which build is actually running
// (a stale cached external_components copy keeps the old value).
static const char *const VSON_FEEDER_REV = "1.5.0";

// Incremented by __wrap_wifi_get_mac_address() each time the linker-wrapped MAC
// hook is actually called. If it stays 0 at boot, the wrap was not linked in
// (wrong/stale build); if it is > 0 but the Local MAC is still the default, the
// MAC is being read through some other path.
extern volatile uint32_t g_mac_hook_calls;

// Voltage (in volts) of the food level phototransistor wired to P22, averaged
// over a few samples. Returns NAN when the ADC is busy or does not answer.
// The IR emitter (P23) must be switched on before calling this.
float read_food_sensor();

// Tiny bookkeeping component: only logs a diagnostic banner in dump_config().
class VsonFeeder : public Component {
 public:
  void dump_config() override;
  float get_setup_priority() const override;
};

}  // namespace vson_feeder
}  // namespace esphome
