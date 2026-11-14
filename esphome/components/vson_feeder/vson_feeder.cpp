// Food level sensor of the VSON WP8621 feeder (BK7231N).
//
// The phototransistor is wired to P22, which is SARADC channel 5. LibreTiny
// only declares ADC3 (P23) for the BK7231N, so analogReadVoltage() cannot be
// used on this pin. The Beken SDK driver is called directly instead, the same
// way LibreTiny's own analogReadVoltage() does.

#include "vson_feeder.h"

#include <Arduino.h>
#include <WiFi.h>
#include <math.h>
#include <sdk_private.h>

#include "esphome/core/log.h"

namespace esphome {
namespace vson_feeder {

static const char *const TAG = "vson_feeder";

volatile uint32_t g_mac_hook_calls = 0;

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

float VsonFeeder::get_setup_priority() const { return setup_priority::LATE; }

void VsonFeeder::dump_config() {
  uint8_t mac[6] = {0};
  // Same path ESPHome uses to print "Local MAC": core helpers -> WiFi.macAddress().
  WiFi.macAddress(mac);

  ESP_LOGCONFIG(TAG, "VSON feeder:");
  ESP_LOGCONFIG(TAG, "  Component revision: %s", VSON_FEEDER_REV);
#ifdef VSON_UNIQUE_MAC
  ESP_LOGCONFIG(TAG, "  Per-device MAC: enabled");
#else
  ESP_LOGCONFIG(TAG, "  Per-device MAC: disabled");
#endif
  // 0 here means the link-time wrap did NOT take effect (stale/old build).
  ESP_LOGCONFIG(TAG, "  MAC hook calls: %u", (unsigned) g_mac_hook_calls);
  ESP_LOGCONFIG(TAG, "  Effective STA MAC: %02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1],
                mac[2], mac[3], mac[4], mac[5]);
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
// We build a stable, locally-administered MAC from the device's ESPHome name --
// unique per feeder -- so each unit keeps a distinct MAC across reboots with no
// storage. The hook is wifi_get_mac_address(): it is the function the Arduino
// WiFi layer (WiFi.macAddress(), which ESPHome reads to print the "Local MAC")
// and the SDK's own netif setup call to read the MAC, and they call it from
// other translation units, so -Wl,-wrap,wifi_get_mac_address (added as a build
// flag by __init__.py) does intercept it. Wrapping cfg_load_mac does not work:
// wifi_get_mac_address calls it in the same file, and --wrap only redirects
// cross-file references.
// ---------------------------------------------------------------------------

#include "esphome/core/application.h"
#include <string.h>

// Beken wifi roles (param_config.h)
#define VSON_ROLE_AP  1
#define VSON_ROLE_STA 2

static void vson_build_mac(uint8_t out[6]) {
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

  out[0] = 0x02;  // locally administered (bit 1), unicast (bit 0 clear)
  out[1] = (h1 >> 0) & 0xFF;
  out[2] = (h1 >> 8) & 0xFF;
  out[3] = (h1 >> 16) & 0xFF;
  out[4] = (h1 >> 24) & 0xFF;
  out[5] = h2 & 0xFF;
}

extern "C" void __wrap_wifi_get_mac_address(char *mac, uint8_t type) {
  esphome::vson_feeder::g_mac_hook_calls++;

  uint8_t base[6];
  vson_build_mac(base);

  if (type == VSON_ROLE_AP) {
    // Same AP/STA relation as the SDK: keep bytes 0..4 and the top of byte 5,
    // flip the low bits (mask = NX_VIRT_DEV_MAX - 1, 4 virtual devices -> 0x03).
    const uint8_t mask = 0x03;
    uint8_t low = base[5];
    memcpy(mac, base, 6);
    mac[5] = (uint8_t) ((base[5] & ~mask) | ((low & mask) ^ mask));
  } else {
    memcpy(mac, base, 6);
  }
}
