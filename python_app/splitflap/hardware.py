from __future__ import annotations

from typing import Any, Callable

from python_app.splitflap.data import translate_letter_to_int


# Default is real I2C access. Set True via startup flag to disable hardware access.
SIMULATE_I2C: bool = False


def send_message_to_display(
    message: str,
    speed: int | None,
    config: dict[str, Any],
    logger: Callable[[str], None],
) -> None:
    
    effective_speed = speed if speed is not None else int(config["default_rotation_speed"])
    prefix = "[SIMULATE] " if SIMULATE_I2C else ""
    logger(f"{prefix}display send (speed={effective_speed}): {message}")
    if not SIMULATE_I2C:
        # Replace this with real split-flap output logic
        try:
            try:
                from smbus2 import SMBus  # type: ignore
            except ImportError:
                from smbus import SMBus  # type: ignore
        except ImportError:
            logger("i2c send skipped - smbus/smbus2 package is not available")
            return

    try:
        with SMBus(int(config["i2c_device"])) as bus:
            address = 1  
            for char in message:

                     
                bus.write_i2c_block_data(address, translate_letter_to_int(char), [effective_speed])
    except OSError as exc:
        logger(f"i2c scan failed to open bus {bus_number}: {exc}")
        return

def initialize_i2c_scan(config: dict[str, Any], logger: Callable[[str], None]) -> None:
    bus_number = int(config["i2c_device"])
    max_address = int(config["num_symbols"])
    found = 0

    if SIMULATE_I2C:
        logger(f"[SIMULATE] starting i2c scan on bus {bus_number}, addresses 1..{max_address}")
        for address in range(1, max_address + 1):
            logger(f"[SIMULATE] i2c address {address} check pass")
            found += 1
        logger(f"[SIMULATE] i2c scan complete - found {found} units")
        return

    try:
        try:
            from smbus2 import SMBus  # type: ignore
        except ImportError:
            from smbus import SMBus  # type: ignore
    except ImportError:
        logger("i2c scan skipped - smbus/smbus2 package is not available")
        return

    logger(f"starting i2c scan on bus {bus_number}, addresses 1..{max_address}")

    try:
        with SMBus(bus_number) as bus:
            for address in range(1, max_address + 1):
                try:
                    bus.read_byte(address)
                    found += 1
                    logger(f"i2c address {address} check pass")
                except OSError as exc:
                    logger(f"i2c address {address} check fail (NACK/error): {exc}")
    except OSError as exc:
        logger(f"i2c scan failed to open bus {bus_number}: {exc}")
        return

    logger(f"i2c scan complete - found {found} units")
