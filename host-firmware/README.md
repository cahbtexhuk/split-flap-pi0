# Split-flap host firmware

ESP32 (Wemos D1 mini ESP32) host that drives up to 10 split-flap units over I2C and exposes a small REST API and settings page over WiFi. Unit firmware lives in [../firmware](../firmware).

## Features

- WiFiManager: connects to a saved network, otherwise opens the `SplitFlap-Setup` access point (portal at `192.168.4.1`)
- REST API to display a message and to clear the display
- Settings page: number of symbols, default speed, first unit address, hostname, slave scan, 100-line console log
- mDNS: `http://<hostname>.local` (default `splitflap`)
- Browser firmware update at `/update` (password protected)
- Optional console log mirror on Serial

## Hardware

| Signal | ESP32 pin |
|--------|-----------|
| SDA    | GPIO21    |
| SCL    | GPIO22    |

- Units are 5 V Arduinos with their own pull-ups, so use a bidirectional 3.3 V to 5 V I2C level shifter between the ESP32 and the bus.
- An optional TCA9548A I2C multiplexer (default address `0x70`) splits the bus into segments, for example units 1-5 on channel 0 and 6-10 on channel 1. Place it in the middle of the chain of units.
- Each unit's address is `0x10 + switch value` (4-bit switch, 0-15). The host's **first unit address** setting is the switch value of the first unit, so a first unit set to switch `1` is `0x11`, the second `0x12`, and so on.

## Build and flash

Requires [PlatformIO](https://platformio.org/install/cli).

```bash
cd host-firmware
pio run                 # build
pio run -t upload       # flash over USB
pio device monitor      # serial monitor, 115200 baud
```

### Build flags

Set in [platformio.ini](platformio.ini) under `build_flags`.

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_SERIAL_LOG` | `0` | `1` mirrors the console log to Serial at 115200 baud |
| `I2C_SDA_PIN` / `I2C_SCL_PIN` | `21` / `22` | I2C pins |
| `I2C_CLOCK_HZ` | `100000` | I2C clock |
| `MAX_ROTATION_SPEED` | `255` | Highest speed accepted; the speed is a single byte sent to the unit's `stepper.setSpeed()`. Lower it to your motors' real limit |
| `UPDATE_PASSWORD` | `changeme` | Password for `/update` (user `admin`). **Change it before flashing** |

## First start

1. Power the board. If no WiFi is saved it starts the `SplitFlap-Setup` access point.
2. Join that network and open `http://192.168.4.1` to pick your SSID and enter the password.
3. The board joins your network, scans for units, and logs its IP and `<hostname>.local`.

If a saved network is unavailable the board retries for 20 seconds, keeps the setup portal open for 3 minutes, then restarts and tries again.

## Settings page

Open `http://<hostname>.local/` (or the board IP).

| Setting | Range | Notes |
|---------|-------|-------|
| Number of symbols | 1-10 | Reduced automatically if it would exceed switch value 15 |
| Default speed | 1-`MAX_ROTATION_SPEED` | Used when a request has no valid speed |
| First unit address | 0-15 | Switch value of the first unit |
| Hostname | up to 31 chars | Letters, digits and `-` only. mDNS updates immediately, the DHCP name after a reboot |
| Use TCA9548A | on/off | Default on. Turn it off when the units are wired straight to the ESP32 |
| TCA address | `0x08`-`0x77` | Default `0x70`. Use a `0x` prefix for hex |
| TCA channels | 0-7, comma-separated | Default `0, 1` |

Settings are stored in flash. Saving settings triggers a scan.

**With the multiplexer on:** a scan selects each configured channel in turn and records which channel every unit answered on. A message is then sent channel by channel: all units on the first channel, then all units on the next. Units not seen by the last scan are spread evenly across the configured channels. If the multiplexer does not acknowledge, its channel's units are reported as failed.

**Scan for slaves** logs the units found per channel, the total found, and the addresses that did not answer. The console log keeps the last 100 lines and refreshes every 3 seconds.

## REST API

No authentication on the API; use it on a trusted network only. Examples assume `http://splitflap.local`.

### `POST /api/message`

```bash
curl -X POST http://splitflap.local/api/message \
  -H "Content-Type: application/json" \
  -d '{"message": "1234567890", "speed": "8"}'
```

| Field | Type | Notes |
|-------|------|-------|
| `message` | string, required | Longer than the number of symbols is silently trimmed. Shorter only updates the first units and leaves the rest unchanged |
| `speed` | number or string, optional | Missing, non-numeric or outside 1-`MAX_ROTATION_SPEED` uses the default speed |

Response `200`:

```json
{"ok": true, "sent": 10, "failed": 0, "speed": 8}
```

`failed` counts units that did not acknowledge. Errors return `400` with `{"ok": false, "error": "..."}` for invalid JSON or a missing `message`.

### `POST /api/clear`

Sends a blank flap to every configured unit at the default speed. Same response shape as `/api/message`.

```bash
curl -X POST http://splitflap.local/api/clear
```

### `GET /api/log`

Returns the console log as plain text.

### Characters

The units have 45 flaps: space, `A-Z`, `Ä Ö Ü`, `0-9`, `:` `.` `-` `?` `!`. Lowercase is uppercased and any other character shows a blank flap.

## Firmware update (browser)

1. Build: `pio run`
2. Open `http://<hostname>.local/update` and sign in as `admin` with `UPDATE_PASSWORD`.
3. Choose `.pio/build/wemos_d1_mini32/firmware.bin` and upload. The board reboots when done.

The password is sent with HTTP Basic auth over plain HTTP. The very first flash must be done over USB.

After the board reboots, check the **Firmware** line in the page footer (and the `boot` line in the console log). It shows the git commit and the build time, for example `acdbe32-dirty 2026-10-24 22:31:38`. It changes on every build, so a new value confirms the update took effect. `-dirty` means there were uncommitted changes in `host-firmware`.

## Postman

Import both files from [postman](postman) into Postman:

- `splitflap.postman_collection.json`
- `splitflap.postman_environment.json`

Select the **Split-flap** environment and edit `base_url` (and `update_password`) if needed.

## REST Client (VS Code)

[splitflap.http](splitflap.http) contains the same requests for the VS Code [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension. Edit `@baseUrl` and `@updatePassword` at the top of the file, then click **Send Request** above any request. It has no response checks, unlike the Postman collection.

## Source layout

| File | Responsibility |
|------|----------------|
| `src/main.cpp` | WiFi setup, boot sequence |
| `src/display.cpp` | I2C writes, scan, character mapping |
| `src/settings.cpp` | Persistent settings |
| `src/web.cpp` | Settings page, REST API, firmware update |
| `src/net.cpp` | mDNS |
| `src/console.cpp` | 100-line console log |
