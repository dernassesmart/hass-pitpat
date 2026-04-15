# PitPat WalkingPad — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/dernassesmart/hass-pitpat/actions/workflows/validate.yml/badge.svg)](https://github.com/dernassesmart/hass-pitpat/actions/workflows/validate.yml)

Control and monitor your **PitPat WalkingPad** treadmill directly from Home Assistant — no extra hardware, no MQTT bridge, no ESP32 required.

Connects via Bluetooth Low Energy (BLE) straight from your Home Assistant host.

---

## What you get

| Entity | Type | Description |
|--------|------|-------------|
| Belt | Switch | Start / stop the belt |
| Speed | Number | Set speed while running (0.5 – 6.0 km/h) |
| Current Speed | Sensor | Live speed in km/h |
| Target Speed | Sensor | Requested speed in km/h |
| Distance | Sensor | Session distance in km |
| Steps | Sensor | Session step count |
| Calories | Sensor | Session calories (kcal) |
| Duration | Sensor | Session time in minutes |
| State | Sensor | stopped / starting / active / standby |

---

## Requirements

- Home Assistant **2023.8** or newer
- Bluetooth on your HA host (built-in, USB dongle, or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy))
- PitPat WalkingPad powered on and in Bluetooth range

> **Tip:** If your HA server doesn't have Bluetooth, a cheap ESP32 running ESPHome as a Bluetooth proxy works perfectly.

---

## Installation

### Option A — HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/dernassesmart/hass-pitpat` as type **Integration**
4. Search for **PitPat WalkingPad** and install it
5. Restart Home Assistant

### Option B — Manual

1. Download this repository as a ZIP
2. Unzip and copy the folder `custom_components/pitpat_walkingpad/` into your HA config folder:
   ```
   config/
   └── custom_components/
       └── pitpat_walkingpad/   ← put it here
   ```
3. Restart Home Assistant

---

## Setup

**Automatic (recommended):**
1. Make sure your WalkingPad is powered on
2. Home Assistant will automatically detect it and show a notification: *"New device found: PitPat-T01"*
3. Click **Configure** and confirm — done!

**Manual (if auto-detection doesn't work):**
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **PitPat WalkingPad**
3. Enter the Bluetooth **MAC address** of your treadmill
   - Use a BLE scanner app like *nRF Connect* → connect to the device → look for the address
4. Give it a name and click **Submit**

The integration will appear as a device with all sensors and controls ready to use.

---

## How it works

The integration talks directly to the WalkingPad over BLE using the protocol documented in [peteh/pacekeeper](https://github.com/peteh/pacekeeper):

- **Service UUID:** `0000fba0-0000-1000-8000-00805f9b34fb`
- **Write characteristic:** `0000fba1-...` — sends 23-byte command packets
- **Notify characteristic:** `0000fba2-...` — receives 31-byte status packets every few seconds

No `ph4-walkingpad` library. No cloud. No bridge. Just `bleak` + Home Assistant's built-in Bluetooth stack.

---

## Troubleshooting

**Device not found during setup**
- Make sure the WalkingPad is powered on (belt light should be on)
- Check that Bluetooth is enabled in HA (Settings → System → Hardware)
- Try scanning with *nRF Connect* to confirm the device is advertising

**Sensors show unavailable**
- The device goes to sleep after a few minutes of inactivity — just step on the belt to wake it
- If it stays unavailable, remove and re-add the integration

**No Bluetooth on my HA host**
- Add an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy) — a ~5€ ESP32 is enough

---

## Credits

- Protocol reverse-engineering: [peteh/pacekeeper](https://github.com/peteh/pacekeeper)
- Integration structure inspired by [madmatah/hass-walkingpad](https://github.com/madmatah/hass-walkingpad)
