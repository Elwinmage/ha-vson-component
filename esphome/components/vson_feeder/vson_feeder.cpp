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
