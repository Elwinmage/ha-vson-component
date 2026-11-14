// Food level sensor of the VSON WP8621 feeder (BK7231N).
//
// The phototransistor is wired to P22, which is SARADC channel 5. LibreTiny
// only declares ADC3 (P23) for the BK7231N, so analogReadVoltage() cannot be
// used on this pin. The Beken SDK driver is called directly instead, the same
// way LibreTiny's own analogReadVoltage() does.

#include "vson_feeder.h"

#include <Arduino.h>
#include <math.h>
#include <sdk_private.h>

namespace esphome {
namespace vson_feeder {

static const uint8_t FOOD_ADC_CHANNEL = 5;   // P22
static const uint8_t FOOD_ADC_SAMPLES = 6;   // the stock firmware averages 6 readings
static const uint32_t ADC_TIMEOUT_MS = 50;   // never block the main loop for long

static uint16_t adc_buffer[1];

static bool read_raw(uint16_t *raw) {
  UINT32 status;
  saradc_desc_t adc;
  saradc_config_param_init(&adc);
  adc.channel = FOOD_ADC_CHANNEL;
  adc.mode = ADC_CONFIG_MODE_CONTINUE;
  adc.pData = adc_buffer;
  adc.data_buff_size = 1;

  DD_HANDLE handle = ddev_open((char *) SARADC_DEV_NAME, &status, (uint32_t) &adc);
  if (handle == DD_HANDLE_UNVALID)
    return false;
  if (status != SARADC_SUCCESS) {
    // ADC already in use (the SDK samples the chip temperature with it)
    ddev_close(handle);
    return false;
  }

  bool done = true;
  uint32_t start = millis();
  while (!adc.has_data || adc.current_sample_data_cnt < 1) {
    if (millis() - start > ADC_TIMEOUT_MS) {
      done = false;
      break;
    }
    delay(1);
  }
  uint8_t run_stop = 0;  // stop
  ddev_control(handle, SARADC_CMD_RUN_OR_STOP_ADC, &run_stop);
  ddev_close(handle);

  if (done)
    *raw = adc_buffer[0];
  return done;
}

float read_food_sensor() {
  uint32_t sum = 0;
  uint8_t count = 0;
  for (uint8_t i = 0; i < FOOD_ADC_SAMPLES; i++) {
    uint16_t raw;
    if (read_raw(&raw)) {
      sum += raw;
      count++;
    }
  }
  if (count == 0)
    return NAN;
  // Same scale as LibreTiny on the BK7231N: 2048 counts for 2.4 V.
  return (float) sum / count * 2.4f / 2048.0f;
}

}  // namespace vson_feeder
}  // namespace esphome

// ---------------------------------------------------------------------------
// Per-device MAC address
//
// LibreTiny gives every BK7231N the same built-in default MAC, and this module
// has no unique hardware ID to derive one from (no eFuse MAC, no flash unique-ID
// opcode). Several feeders on one network would therefore share a MAC.
//
// With -Wl,-wrap,cfg_load_mac (added by vson_mac.py.script), the SDK's MAC
// loader is routed here instead. We build a stable, locally-administered MAC
// from the device's ESPHome name — which is unique per feeder — so each unit
// keeps a distinct MAC across reboots without any storage.
// ---------------------------------------------------------------------------

#include "esphome/core/application.h"

extern "C" void __wrap_cfg_load_mac(uint8_t *mac) {
  const std::string &name = esphome::App.get_name();

  // FNV-1a over the name, then a second mixed pass for the last byte.
  uint32_t h1 = 2166136261u;
  for (char c : name) {
    h1 ^= (uint8_t) c;
    h1 *= 16777619u;
  }
  uint32_t h2 = h1 ^ 0x9e3779b9u;
  for (char c : name) {
    h2 = (h2 << 5) | (h2 >> 27);
    h2 += (uint8_t) c;
  }

  mac[0] = 0x02;  // locally administered (bit 1), unicast (bit 0 clear)
  mac[1] = (h1 >> 0) & 0xFF;
  mac[2] = (h1 >> 8) & 0xFF;
  mac[3] = (h1 >> 16) & 0xFF;
  mac[4] = (h1 >> 24) & 0xFF;
  mac[5] = h2 & 0xFF;
}
