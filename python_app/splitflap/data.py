from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Callable


APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "num_symbols": 10,
    "default_rotation_speed": 80,
    "i2c_device": 1,
    "log_line_limit": 200,
    "default_prop_clock_time": "22:00",
}

FLAP_LETTERS: tuple[str, ...] = tuple(" ABCDEFGHIJKLMNOPQRSTUVWXYZ$&#0123456789:,.-?!")
ALLOWED_SYMBOLS: frozenset[str] = frozenset(FLAP_LETTERS)

CONFIG: dict[str, Any] = {}
CONFIG_LOCK = Lock()

LOG_LINES: deque[str] = deque(maxlen=DEFAULT_CONFIG["log_line_limit"])
LOG_LOCK = Lock()

CLOCK_LOCK = Lock()
CLOCK_START_TIME = "12:00"
CLOCK_CURRENT_TIME = "12:00"

DISPLAY_SENDER: Callable[[str, int | None], None] | None = None


def set_display_sender(sender: Callable[[str, int | None], None]) -> None:
    global DISPLAY_SENDER
    DISPLAY_SENDER = sender


def console_print(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_LOCK:
        LOG_LINES.append(f"[{timestamp}] {message}")


def get_log_lines() -> list[str]:
    with LOG_LOCK:
        return list(LOG_LINES)


def set_log_limit(limit: int) -> None:
    global LOG_LINES
    with LOG_LOCK:
        current_lines = list(LOG_LINES)
        LOG_LINES = deque(current_lines[-limit:], maxlen=limit)


def validate_time_24h(value: str) -> bool:
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        return False
    return True


def sanitize_config(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(raw)

    try:
        cfg["num_symbols"] = max(1, int(cfg["num_symbols"]))
    except (TypeError, ValueError):
        cfg["num_symbols"] = DEFAULT_CONFIG["num_symbols"]

    try:
        cfg["default_rotation_speed"] = max(1, int(cfg["default_rotation_speed"]))
    except (TypeError, ValueError):
        cfg["default_rotation_speed"] = DEFAULT_CONFIG["default_rotation_speed"]

    try:
        cfg["i2c_device"] = max(0, int(cfg["i2c_device"]))
    except (TypeError, ValueError):
        cfg["i2c_device"] = DEFAULT_CONFIG["i2c_device"]

    try:
        cfg["log_line_limit"] = max(10, int(cfg["log_line_limit"]))
    except (TypeError, ValueError):
        cfg["log_line_limit"] = DEFAULT_CONFIG["log_line_limit"]

    clock_default = str(cfg.get("default_prop_clock_time", DEFAULT_CONFIG["default_prop_clock_time"]))
    if not validate_time_24h(clock_default):
        clock_default = DEFAULT_CONFIG["default_prop_clock_time"]
    cfg["default_prop_clock_time"] = clock_default
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        cfg = dict(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg

    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        loaded = dict(DEFAULT_CONFIG)

    cfg = sanitize_config(loaded)
    save_config(cfg)
    return cfg


def initialize_clock_state() -> None:
    global CLOCK_START_TIME, CLOCK_CURRENT_TIME
    default_time = CONFIG.get("default_prop_clock_time", DEFAULT_CONFIG["default_prop_clock_time"])
    with CLOCK_LOCK:
        CLOCK_START_TIME = default_time
        CLOCK_CURRENT_TIME = default_time


def startup_initialize() -> None:
    global CONFIG
    CONFIG = load_config()
    set_log_limit(int(CONFIG["log_line_limit"]))
    initialize_clock_state()


def get_config() -> dict[str, Any]:
    with CONFIG_LOCK:
        return dict(CONFIG)


def apply_config(new_config: dict[str, Any]) -> None:
    global CONFIG
    sanitized = sanitize_config(new_config)
    with CONFIG_LOCK:
        CONFIG = sanitized
        save_config(CONFIG)
    set_log_limit(CONFIG["log_line_limit"])
    initialize_clock_state()
    console_print("configuration saved and reloaded")


def translate_letter_to_int(char: str) -> int:
    """Return the flap index of char, or -1 if not in FLAP_LETTERS."""
    try:
        return FLAP_LETTERS.index(char)
    except ValueError:
        return -1


def sanitize_message(raw: str) -> str:
    upper = raw.upper()
    return "".join(ch if ch in ALLOWED_SYMBOLS else " " for ch in upper)


def align_text(text: str, width: int, alignment: str) -> str:
    trimmed = text[:width]
    if alignment == "right":
        return trimmed.rjust(width)
    if alignment == "center":
        return trimmed.center(width)
    return trimmed.ljust(width)


def to_datetime(time_text: str) -> datetime:
    return datetime.strptime(time_text, "%H:%M")


def format_time(value: datetime) -> str:
    return value.strftime("%H:%M")


def add_hours_with_rounding(time_text: str, hours: int) -> str:
    current = to_datetime(time_text)
    minutes = current.minute

    if minutes == 0:
        result = current + timedelta(hours=hours)
        return format_time(result)

    rounded_up = (current + timedelta(hours=1)).replace(minute=0)

    if minutes < 30:
        if hours == 1:
            return format_time(rounded_up)
        if hours == 2:
            return format_time(rounded_up + timedelta(hours=1))

    return format_time(rounded_up + timedelta(hours=hours))


def get_clock_state() -> dict[str, str]:
    with CLOCK_LOCK:
        return {
            "start_time": CLOCK_START_TIME,
            "current_time": CLOCK_CURRENT_TIME,
        }


def _send_clock_to_display() -> None:
    if DISPLAY_SENDER is None:
        return
    width = int(CONFIG.get("num_symbols", DEFAULT_CONFIG["num_symbols"]))
    centered = CLOCK_CURRENT_TIME.center(width)
    DISPLAY_SENDER(centered, None)


def set_clock_start(time_text: str) -> dict[str, str]:
    global CLOCK_START_TIME, CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_START_TIME = time_text
        CLOCK_CURRENT_TIME = time_text
    console_print(f"clock start time overridden to {time_text}")
    _send_clock_to_display()
    return get_clock_state()


def reset_clock() -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_CURRENT_TIME = CLOCK_START_TIME
        current = CLOCK_CURRENT_TIME
    console_print(f"clock reset to start time {current}")
    _send_clock_to_display()
    return get_clock_state()


def add_minutes_to_clock(minutes: int) -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        current = to_datetime(CLOCK_CURRENT_TIME)
        CLOCK_CURRENT_TIME = format_time(current + timedelta(minutes=minutes))
        updated = CLOCK_CURRENT_TIME
    console_print(f"clock advanced by {minutes} minutes to {updated}")
    _send_clock_to_display()
    return get_clock_state()


def add_hours_to_clock(hours: int) -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_CURRENT_TIME = add_hours_with_rounding(CLOCK_CURRENT_TIME, hours)
        updated = CLOCK_CURRENT_TIME
    console_print(f"clock advanced by {hours} hour(s) to {updated}")
    _send_clock_to_display()
    return get_clock_state()
