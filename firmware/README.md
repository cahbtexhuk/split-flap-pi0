# Split-Flap Arduino Firmware (PlatformIO)

This is a PlatformIO wrapper around the Arduino sketches from the
[split-flap](https://github.com) repo (`Unit/Unit.ino` and
`EEPROM_Write_Offset/EEPROM_Write_Offset.ino`). That repo is treated as
**read-only** — sketches are copied here (as `.cpp` with explicit forward
declarations, since this PlatformIO version does not reliably handle
multiple `.ino` sketches in one project) and any firmware fixes/changes
happen in this `firmware/` folder instead.

## Targets

| Environment      | Source                                   | Purpose                                              |
|-------------------|-------------------------------------------|-------------------------------------------------------|
| `unit`            | `src/unit/Unit.cpp`                       | Main split-flap unit firmware (stepper + I2C slave)   |
| `eeprom_offset`   | `src/eeprom_offset/EEPROM_Write_Offset.cpp` | One-off tool to write the hall-sensor calibration offset into EEPROM |

Both target an Arduino Nano (ATmega328P, new/optiboot bootloader) by default.

## Prerequisites

- [PlatformIO CLI](https://platformio.org/install/cli) or the PlatformIO IDE
  extension for VS Code.
- USB cable connected to the Nano.

## Building

From this folder:

```bash
pio run -e unit
pio run -e eeprom_offset
```

Or build both:

```bash
pio run -e unit -e eeprom_offset
```

## Flashing

### Unit firmware (every split-flap unit)

```bash
pio run -e unit -t upload
```

### EEPROM offset tool

Only needed when (re)calibrating a unit's hall-sensor offset:

```bash
pio run -e eeprom_offset -t upload
```

After uploading, open the serial monitor to read/write the offset:

```bash
pio device monitor -e eeprom_offset
```

Type a new integer offset and press Enter to write it to EEPROM. **Re-flash
the `unit` environment afterwards** to return the Nano to normal operation —
the EEPROM tool sketch does not drive the stepper or answer I2C requests.

## Changing the USB port

By default `platformio.ini` sets:

```ini
upload_port = COM3
```

To flash a different port, either:

1. Edit `upload_port` in [platformio.ini](platformio.ini), or
2. Override it on the command line without editing the file:

   ```bash
   pio run -e unit -t upload --upload-port COM7
   ```

To list available ports:

```bash
pio device list
```

## Changing the board / bootloader variant

Both environments share `board = nanoatmega328new` (Nano with the newer
optiboot bootloader, 115200 baud upload). If uploading fails with a
sync/timeout error, your Nano clone likely has the **old bootloader**
instead. Change the shared `[env]` section in [platformio.ini](platformio.ini):

```ini
board = nanoatmega328old
```

## Serial debug output

`Unit.cpp` has `SERIAL_ENABLE` commented out by default (recommended for
normal operation — see the project's I2C reliability notes). To get debug
logs over serial for troubleshooting, uncomment the line near the top of
[src/unit/Unit.cpp](src/unit/Unit.cpp):

```cpp
#define SERIAL_ENABLE
```

Then re-flash and open the serial monitor:

```bash
pio device monitor -e unit
```

Remember to comment it back out before flashing units for normal use.
