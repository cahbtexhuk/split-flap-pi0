from __future__ import annotations

import time
from typing import Any, Callable

from splitflap.data import translate_letter_to_int


# Default is real I2C access. Set True via startup flag to disable hardware access.
SIMULATE_I2C: bool = False

# Offset added to slave index to avoid reserved I2C addresses 0x00-0x07, must match Unit.ino I2C_ADDRESS_BASE
I2C_ADDRESS_BASE: int = 0x10


def send_message_to_display(
    message: str,
    speed: int | None,
    config: dict[str, Any],
    logger: Callable[[str], None],
) -> None:
    
    effective_speed = speed if speed is not None else int(config["default_rotation_speed"])
    prefix = "[SIMULATE] " if SIMULATE_I2C else ""
    logger(f"{prefix}display send (speed={effective_speed}): {message}")
    
    if SIMULATE_I2C:
        return

    try:
        try:
            from smbus2 import SMBus  # type: ignore
        except ImportError:
            from smbus import SMBus  # type: ignore
    except ImportError:
        logger("i2c send skipped - smbus/smbus2 package is not available")
        return

    bus_num = int(config["i2c_device"])

    try:
        with SMBus(bus_num) as bus:
            # Loop over characters and send to ascending slave addresses (base to base+9)
            for i, char in enumerate(message):
                slave_address = I2C_ADDRESS_BASE + i

                if i >= 10:
                    break  # Stop if message exceeds display capacity
                
                char_byte = int(translate_letter_to_int(char))
                speed_byte = int(effective_speed)
                
                try:
                    # Sends Slave Addr -> Byte 1 (Char / Register) -> Byte 2 (Speed)
                    bus.write_i2c_block_data(slave_address, char_byte, [speed_byte])
                    time.sleep(0.001)
                except OSError as slave_exc:
                    # Prevents a single slave error (NACK) from crashing the Flask route
                    logger(f"i2c write failed for slave {slave_address}: {slave_exc}")

    except OSError as exc:
        logger(f"i2c write failed to open bus {bus_num}: {exc}")
        return


def initialize_i2c_scan(config: dict[str, Any], logger: Callable[[str], None]) -> None:
    bus_num = int(config["i2c_device"])
    max_address = int(config["num_symbols"])
    found = 0

    if SIMULATE_I2C:
        logger(f"[SIMULATE] starting i2c scan on bus {bus_num}, addresses {I2C_ADDRESS_BASE:#x}..{I2C_ADDRESS_BASE + max_address - 1:#x}")
        for address in range(I2C_ADDRESS_BASE, I2C_ADDRESS_BASE + max_address):
            logger(f"[SIMULATE] i2c address {address:#x} check pass")
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

    logger(f"starting i2c scan on bus {bus_num}, addresses {I2C_ADDRESS_BASE:#x}..{I2C_ADDRESS_BASE + max_address - 1:#x}")

    try:
        with SMBus(bus_num) as bus:
            for address in range(I2C_ADDRESS_BASE, I2C_ADDRESS_BASE + max_address):
                try:
                    bus.read_byte(address)
                    found += 1
                    logger(f"i2c address {address:#x} check pass")
                except OSError as exc:
                    logger(f"i2c address {address:#x} check fail (NACK/error): {exc}")
    except OSError as exc:
        logger(f"i2c scan failed to open bus {bus_num}: {exc}")
        return

    logger(f"i2c scan complete - found {found} units")