# VSON 🐟
> Part of the [**ReefTech Project Ecosystem**](https://elwinmage.github.io/reeftank/)
<p align="center">
  <img src="icon.png"  width="50%"/>
</p>

[![IoT Class](https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-vson-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-vson-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-vson-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-vson-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-vson-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-vson-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-vson-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-vson-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-vson-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-vson-component)

# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" width="5%"/>](https://github.com/Elwinmage/ha-vson-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" width="5%"/>](https://github.com/Elwinmage/ha-vson-component/blob/main/doc/fr/README.fr.md)

Control your VSON aquarium devices from Home Assistant through the VSON cloud API (`apis.myvsoncloud.com`). The WP8621 automatic fish feeder is fully supported; every other VSON device on your account is detected generically (online state + manual refresh), and new families are easy to add.

---

<!-- ecosystem:start -->

## Related projects

The ReefTech projects fit together: the integrations bring your equipment into Home Assistant, the card displays and drives it, and the backup keeps it running through an outage. Each one also works on its own.

<p align="center"><a href="https://elwinmage.github.io/reeftank/"><img src="https://raw.githubusercontent.com/Elwinmage/reeftank/main/assets/flower/ecosystem-flower.png" width="480" alt="ReefTech project ecosystem" /></a></p>

<table>
  <tr>
    <th width="100px"></th>
    <th>Project</th>
    <th>What it does</th>
    <th>Works with</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Red Sea ReefBeat devices, controlled locally with no cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun and ReefWave.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Aqua Medic pumps through the Gizwits cloud API: EcoDrift and SmartDrift wavemakers, DC Runner return and skimmer pumps.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-vson-component/main/icon.png" width="64" alt="ha-vson-component" /></td>
    <td>🐟<br /><b>ha-vson-component</b><br /><i>(this repository)</i></td>
    <td>VSON devices through the VSON cloud API: WP8621 automatic fish feeder (feed now, battery, low-food alert), and generic detection of any other VSON device on the account.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Cleaning and wear tracking for the equipment Home Assistant cannot talk to.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interactive graphical view of each device on your dashboard. Reads the integrations through the shared <code>reef_role</code> contract, with no card-side configuration.</td>
    <td>all integrations, and ha-reeftank-component for the aquarium</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reeftank-component/main/icon.png" width="64" alt="ha-reeftank-component" /></td>
    <td>🐟<br /><a href="https://github.com/Elwinmage/ha-reeftank-component"><b>ha-reeftank-component</b></a></td>
    <td>A living picture of your tank on the dashboard. Stores the aquariums and their livestock, records the feedings.</td>
    <td>ha-reef-card</td>
  </tr>
</table>

<!-- ecosystem:end -->

---

## Supported devices

| Device | Model `type` | Entities |
|---|---|---|
| **WP8621 automatic fish feeder** (variants N/E/H/F/B/P/A/C) | `8621` | Feed now (button), Battery (%), Firmware, Food shortage (problem), Online, Scheduled feeding (switch), Refresh |
| **Any other VSON device** | *detected* | Online, Refresh |

The feeder is driven by the cloud's `Bley` endpoints. Other families are added in `custom_components/vson/devices.py` by declaring a new `DeviceFamily`; no change to the platforms is needed.

## How it works

Everything goes through plain HTTPS POST requests against `apis.myvsoncloud.com`, reverse-engineered from the official VSON Android app:

- credentials are 3DES-encrypted at login (there is no proprietary socket protocol);
- the session token is carried, re-encrypted, in a request header;
- the feeder's realtime state (battery, low-food, firmware) is polled from `queryBleyHomepage`, and a manual feed is `updateBleyFeed`.

No credentials or tokens ever leave your Home Assistant instance except toward the VSON cloud.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category *Integration*).
2. Install **VSON**, then restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → VSON**.

### Manual

Copy `custom_components/vson` into your Home Assistant `config/custom_components/` folder and restart.

## Configuration

Sign in with the same **phone number or e-mail** and **password** you use in the VSON mobile app. You can tune the refresh interval (10–600 s, default 30 s) at setup and later in the integration options.

## Ecosystem integration

Every entity publishes a stable `reef_role` state attribute (e.g. `online`, `food_shortage`, `feed`). This is the shared contract the ReefTech ecosystem uses: [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) and the shared blueprints discover VSON entities through it, with no per-integration configuration.

## FAQ

**Is this official?** No. It is an independent, interoperability-focused integration built from the public mobile app. Use your own account.

**My feeder is not detected as a feeder.** Enable debug logging for `custom_components.vson` and open an issue with the device's `type` code — a new `DeviceFamily` can be mapped for it.

**Does it work without the cloud?** No, this integration talks to the VSON cloud. A local-firmware (ESPHome) route for the WP8621 is a separate, hardware-level effort.

## Development

```bash
pip install -r requirements.test.txt
pre-commit install
pytest
```

The CI mirrors the pre-commit hooks: ruff, hassfest, HACS validation, translation check and pytest.
