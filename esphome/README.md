# FishFeeder — ESPHome on the stock BK7231N

Run [ESPHome](https://esphome.io) on the **VSON WP8621** automatic fish feeder
**without replacing its chip**. The feeder keeps its original Beken **BK7231N**
module (marked *BL2028N*, module *WIFI001_V20*); only the firmware changes. You
get a native Home Assistant device: on-device feeding schedule, food-level
sensor, manual feed, and the status LED — no cloud.

The firmware integrates with [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
through the project name `vson.fish_feeder`.

## Why this needs a dedicated config

Two things make this module special, both handled by the config and the
`vson_feeder` component so you don't have to think about them:

- **Zero flash-encryption keys.** Unlike Tuya modules, this BK7231N runs the
  flash in clear text. The config builds a plain (non-encrypted) image with
  `board_build.bkcrypt_coeffs: "0000…"`. A standard (Tuya-key) image does not
  boot on it.
- **A non-Tuya bootloader that stays in place.** The stock bootloader is kept,
  and it does not understand LibreTiny's OTA package. The `vson_feeder`
  component builds the OTA image in the format this bootloader installs, so
  **after the first UART flash, every update is wireless.**

## Configuration

The device YAML is **[`fishfeeder.yaml`](fishfeeder.yaml)**. It pulls the
`vson_feeder` component and each feeding slot straight from this repository, so
it works as-is in the ESPHome Builder add-on (no local files to create):

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/Elwinmage/ha-vson-component
      ref: main
      path: esphome/components
    components: [vson_feeder]

vson_feeder:

bk72xx:
  board: generic-bk7231n-qfn32-tuya
  framework:
    uart_port: 1          # logs on UART1 (P10/P11); P0/P1 drive the LEDs
```

Before building, set:

- `wifi_ssid` / `wifi_password` in your `secrets.yaml`;
- your own API encryption key and fallback-hotspot password in `fishfeeder.yaml`
  (the ones shipped are placeholders).

The number of feeding slots is the number of `feed_slot_*` blocks in the
`packages:` section — add or remove one to change it.

## Step 1 — First flash, over UART (once)

The first flash must be done over a wired **USB-to-UART (3.3 V)** adapter. It
writes only the app, so the stock bootloader is preserved.

### Wiring

![UART wiring on the WP8621 board](wiring.png)

| USB-TTL adapter | Feeder board | Where on the photo |
|---|---|---|
| TX | **RX** | middle, lower half |
| RX | **TX** | just below RX |
| GND | **GND** | top right (next to the black wire) |
| 3.3 V / VCC | — | **do not connect** |

**Do not power the board during the first flash — no DC jack, and no adapter
VCC.** In bootloader mode the module draws almost nothing and runs off the TX
line alone; adding a second supply (the jack *or* the adapter's 3.3 V) made this
unit reset instead of flashing. So connect **only GND + TX + RX**. (If your unit
stays completely dead with just those three, connect the adapter's 3.3 V to VCC
— but never together with the DC jack. The jack is for normal operation, once
the feeder is reassembled, not for the wired flash.)

> Tip: back up the original firmware first (same wiring), so you can always
> return to stock:
> `ltchiptool flash read backup.bin -f bk7231n -d /dev/ttyUSB0`

### Flash it

**Option A — from Home Assistant (ESPHome Builder).** Plug the USB-TTL adapter
into the machine running the ESPHome dashboard, then on the device choose
**Install → Plug into the computer running ESPHome Dashboard** and pick the
serial port. ESPHome flashes over UART with `ltchiptool` under the hood. When it
says *Connecting…*, **reset the module** so the ROM loader catches it: briefly
unplug and replug the adapter (that is what powers the board), a few times if
needed.

**Option B — command line.**

```bash
ltchiptool flash write firmware.uf2 -d /dev/ttyUSB0
```

Same thing: on *Connecting…*, unplug/replug the adapter until it connects. Take
the `firmware.uf2` that the ESPHome build produces.

Once flashed, put the board back in the feeder and power it normally (its DC
jack). It boots ESPHome and joins your WiFi; the blue LED stops blinking once
connected. Adopt it in Home Assistant.

## Step 2 — Updates, wireless (from now on)

No more wires. In ESPHome Builder use **Install → Wirelessly**, or let Home
Assistant offer the update. The `vson_feeder` component packs the image in the
stock bootloader's format; look for this line in the build log to confirm it
ran:

```
VSON OTA: … bytes of XZ (…%), installed by the stock bootloader
```

After *OTA successful*, the feeder stays **silent for about a minute** while the
bootloader unpacks the new firmware — **do not power it off during that time.**
An interrupted upload or a power cut is safe: the previous firmware keeps
running and the install simply restarts on the next boot.

## Status LED

A single bi-color LED (pins P0/P1):

- **Blue** blinks while WiFi is disconnected (boot included), off once connected.
- **Red** blinks while food is missing, off otherwise.

If the colors are swapped on your unit, exchange `pin_led_blue` and
`pin_led_red` at the top of `fishfeeder.yaml`.

## Hardware wiring (motor, sensors)

Opening the feeder and the connections of the motor, trap switch and food
sensor are described in the Home Assistant community thread:
[VSON WP8621 V1.2 fish feeder](https://community.home-assistant.io/t/vson-wp8621-v12-fish-feeder/759621).
The pin map used by this firmware (read from the stock firmware) is at the top
of `fishfeeder.yaml`.

## Troubleshooting

- **The old firmware boots again after an OTA.** The OTA image was not in the
  stock-bootloader format. Check the `VSON OTA:` line is in the build log; if
  not, the component is served from cache — set `refresh: always` on the
  `vson_feeder` external component for one build.
- **`ltchiptool` never connects.** Keep only GND + TX + RX (no jack, no VCC) and
  unplug/replug the adapter while it says *Connecting…*. If still nothing, swap
  the board's RX/TX. If the board seems dead, add the adapter's 3.3 V to VCC
  (without the jack).
- **Nothing boots after flashing.** Re-flash; an unstable supply during the
  write can leave an incomplete image. Once flashed, remember the app itself
  needs real power — run it from the feeder's DC jack, not from the TX line.
