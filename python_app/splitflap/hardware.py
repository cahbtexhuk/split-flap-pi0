from __future__ import annotations

import time
from typing import Any, Callable

from splitflap.data import (
    get_slave_channel_map,
    get_tca_channel_list,
    set_slave_channel_map,
    translate_letter_to_int,
)


# Default is real I2C access. Set True via startup flag to disable hardware access.
SIMULATE_I2C: bool = False

# Offset added to slave index to avoid reserved I2C addresses 0x00-0x07, must match Unit.ino I2C_ADDRESS_BASE
I2C_ADDRESS_BASE: int = 0x10


def select_tca_channel(
    bus: Any,
    tca_address: int,
    channel: int,
    logger: Callable[[str], None],
) -> bool:
    if SIMULATE_I2C:
        logger(f"[SIMULATE] selected tca channel {channel} on {tca_address:#x}")
        return True

    try:
        bus.write_byte(tca_address, 1 << channel)
        time.sleep(0.001)
        return True
    except OSError as exc:
        logger(f"failed to select tca channel {channel} on {tca_address:#x}: {exc}")
        return False


def send_message_to_display(
    message: str,
    speed: int | None,
    config: dict[str, Any],
    logger: Callable[[str], None],
) -> None:
    effective_speed = speed if speed is not None else int(config["default_rotation_speed"])
    prefix = "[SIMULATE] " if SIMULATE_I2C else ""
    logger(f"{prefix}display send (speed={effective_speed}): {message}")

    tca_enabled = bool(config.get("tca_enabled", True))
    tca_address = int(config.get("tca_address", 0x70))
    channels = get_tca_channel_list(config)
    channel_map = get_slave_channel_map()
    num_symbols = max(1, int(config.get("num_symbols", 10)))

    # Build list of items to send: (channel, slave_address, char, char_byte, speed_byte)
    items_to_send: list[tuple[int, int, str, int, int]] = []
    for i, char in enumerate(message):
        if i >= 10:
            break

        slave_address = I2C_ADDRESS_BASE + int(config["first_unit_address"]) + i
        char_byte = int(translate_letter_to_int(char))
        speed_byte = int(effective_speed)

        if tca_enabled:
            assigned_channel = channel_map.get(slave_address)
            if assigned_channel is None:
                ch_idx = min(len(channels) - 1, (i * len(channels)) // num_symbols)
                assigned_channel = channels[ch_idx]
        else:
            assigned_channel = 0

        items_to_send.append((assigned_channel, slave_address, char, char_byte, speed_byte))

    if SIMULATE_I2C:
        if tca_enabled:
            for channel in channels:
                channel_items = [item for item in items_to_send if item[0] == channel]
                if not channel_items:
                    continue
                select_tca_channel(None, tca_address, channel, logger)
                for _, s_addr, ch, c_byte, sp_byte in channel_items:
                    logger(f"[SIMULATE] wrote char '{ch}' ({c_byte:#x}) to slave {s_addr:#x} (speed={sp_byte}) on channel {channel}")
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
            if tca_enabled:
                for channel in channels:
                    channel_items = [item for item in items_to_send if item[0] == channel]
                    if not channel_items:
                        continue

                    if not select_tca_channel(bus, tca_address, channel, logger):
                        continue

                    for _, slave_address, _, char_byte, speed_byte in channel_items:
                        try:
                            # Sends Slave Addr -> Byte 1 (Char / Register) -> Byte 2 (Speed)
                            bus.write_i2c_block_data(slave_address, char_byte, [speed_byte])
                            time.sleep(0.001)
                        except OSError as slave_exc:
                            logger(f"i2c write failed for slave {slave_address:#x} on channel {channel}: {slave_exc}")
            else:
                for _, slave_address, _, char_byte, speed_byte in items_to_send:
                    try:
                        bus.write_i2c_block_data(slave_address, char_byte, [speed_byte])
                        time.sleep(0.001)
                    except OSError as slave_exc:
                        logger(f"i2c write failed for slave {slave_address:#x}: {slave_exc}")

    except OSError as exc:
        logger(f"i2c write failed to open bus {bus_num}: {exc}")
        return


def initialize_i2c_scan(config: dict[str, Any], logger: Callable[[str], None]) -> None:
    bus_num = int(config["i2c_device"])
    max_address = int(config["num_symbols"])
    first_address = I2C_ADDRESS_BASE + int(config["first_unit_address"])
    last_address = first_address + max_address - 1
    tca_enabled = bool(config.get("tca_enabled", True))
    tca_address = int(config.get("tca_address", 0x70))
    channels = get_tca_channel_list(config)
    found = 0
    new_channel_map: dict[int, int] = {}

    if SIMULATE_I2C:
        if tca_enabled:
            logger(f"[SIMULATE] starting multi-channel i2c scan on bus {bus_num} via TCA9548A {tca_address:#x}")
            for channel in channels:
                select_tca_channel(None, tca_address, channel, logger)
                logger(f"[SIMULATE] scanning channel {channel}, addresses {first_address:#x}..{last_address:#x}")
                for i, address in enumerate(range(first_address, last_address + 1)):
                    sim_channel = channels[min(len(channels) - 1, (i * len(channels)) // max(1, max_address))]
                    if sim_channel == channel:
                        new_channel_map[address] = channel
                        logger(f"[SIMULATE] i2c address {address:#x} check pass (channel {channel})")
                        found += 1
            set_slave_channel_map(new_channel_map)
            logger(f"[SIMULATE] i2c scan complete - found {found} units across {len(channels)} channels")
        else:
            logger(f"[SIMULATE] starting i2c scan on bus {bus_num}, addresses {first_address:#x}..{last_address:#x}")
            for address in range(first_address, last_address + 1):
                logger(f"[SIMULATE] i2c address {address:#x} check pass")
                found += 1
            set_slave_channel_map({})
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

    if tca_enabled:
        logger(f"starting multi-channel i2c scan on bus {bus_num} via TCA9548A {tca_address:#x}")
        try:
            with SMBus(bus_num) as bus:
                for channel in channels:
                    if not select_tca_channel(bus, tca_address, channel, logger):
                        continue

                    logger(f"scanning channel {channel}, addresses {first_address:#x}..{last_address:#x}")
                    for address in range(first_address, last_address + 1):
                        try:
                            bus.read_byte(address)
                            found += 1
                            if address not in new_channel_map:
                                new_channel_map[address] = channel
                            logger(f"i2c address {address:#x} check pass (channel {channel})")
                        except OSError as exc:
                            logger(f"i2c address {address:#x} check fail on channel {channel} (NACK/error): {exc}")
        except OSError as exc:
            logger(f"i2c scan failed to open bus {bus_num}: {exc}")
            return

        set_slave_channel_map(new_channel_map)
        logger(f"i2c scan complete - found {found} units across {len(channels)} channels")
    else:
        logger(f"starting i2c scan on bus {bus_num}, addresses {first_address:#x}..{last_address:#x}")
        try:
            with SMBus(bus_num) as bus:
                for address in range(first_address, last_address + 1):
                    try:
                        bus.read_byte(address)
                        found += 1
                        logger(f"i2c address {address:#x} check pass")
                    except OSError as exc:
                        logger(f"i2c address {address:#x} check fail (NACK/error): {exc}")
        except OSError as exc:
            logger(f"i2c scan failed to open bus {bus_num}: {exc}")
            return

        set_slave_channel_map({})
        logger(f"i2c scan complete - found {found} units")