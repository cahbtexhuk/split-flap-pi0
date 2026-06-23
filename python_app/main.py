from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "num_symbols": 10,
    "default_rotation_speed": 40,
    "i2c_device": 1,
    "log_line_limit": 200,
    "default_prop_clock_time": "12:00",
}

ALLOWED_SYMBOLS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:!?-. ,")

CONFIG: dict[str, Any] = {}
CONFIG_LOCK = Lock()

LOG_LINES: deque[str] = deque(maxlen=DEFAULT_CONFIG["log_line_limit"])
LOG_LOCK = Lock()

CLOCK_LOCK = Lock()
CLOCK_START_TIME = "12:00"
CLOCK_CURRENT_TIME = "12:00"

app = Flask(__name__)
app.secret_key = "split-flap-dev-secret"


def console_print(message: str) -> None:
    """Append a timestamped line to the in-app log buffer."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_LOCK:
        LOG_LINES.append(f"[{timestamp}] {message}")


def set_log_limit(limit: int) -> None:
    """Resize in-memory log storage while keeping most recent entries."""
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
    # Keep file normalized whenever invalid/partial values were found.
    save_config(cfg)
    return cfg


def apply_config(new_config: dict[str, Any]) -> None:
    global CONFIG
    sanitized = sanitize_config(new_config)
    with CONFIG_LOCK:
        CONFIG = sanitized
        save_config(CONFIG)
    set_log_limit(CONFIG["log_line_limit"])
    initialize_clock_state()
    console_print("configuration saved and reloaded")


def initialize_clock_state() -> None:
    global CLOCK_START_TIME, CLOCK_CURRENT_TIME
    default_time = CONFIG.get("default_prop_clock_time", DEFAULT_CONFIG["default_prop_clock_time"])
    with CLOCK_LOCK:
        CLOCK_START_TIME = default_time
        CLOCK_CURRENT_TIME = default_time


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


def send_message_to_display(message: str, speed: int | None = None) -> None:
    """
    Hardware placeholder. Replace this with real split-flap output logic.
    """
    effective_speed = speed if speed is not None else int(CONFIG["default_rotation_speed"])
    console_print(f"display send (speed={effective_speed}): {message}")


def initialize_i2c_scan() -> None:
    bus_number = int(CONFIG["i2c_device"])
    max_address = int(CONFIG["num_symbols"])
    found = 0

    try:
        try:
            from smbus2 import SMBus  # type: ignore
        except ImportError:
            from smbus import SMBus  # type: ignore
    except ImportError:
        console_print("i2c scan skipped - smbus/smbus2 package is not available")
        return

    console_print(f"starting i2c scan on bus {bus_number}, addresses 1..{max_address}")

    try:
        with SMBus(bus_number) as bus:
            for address in range(1, max_address + 1):
                try:
                    bus.read_byte(address)
                    found += 1
                    console_print(f"i2c address {address} check pass")
                except OSError as exc:
                    console_print(f"i2c address {address} check fail (NACK/error): {exc}")
    except OSError as exc:
        console_print(f"i2c scan failed to open bus {bus_number}: {exc}")
        return

    console_print(f"i2c scan complete - found {found} units")


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


def set_clock_start(time_text: str) -> dict[str, str]:
    global CLOCK_START_TIME, CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_START_TIME = time_text
        CLOCK_CURRENT_TIME = time_text
    console_print(f"clock start time overridden to {time_text}")
    return get_clock_state()


def reset_clock() -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_CURRENT_TIME = CLOCK_START_TIME
        current = CLOCK_CURRENT_TIME
    console_print(f"clock reset to start time {current}")
    return get_clock_state()


def add_minutes_to_clock(minutes: int) -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        current = to_datetime(CLOCK_CURRENT_TIME)
        CLOCK_CURRENT_TIME = format_time(current + timedelta(minutes=minutes))
        updated = CLOCK_CURRENT_TIME
    console_print(f"clock advanced by {minutes} minutes to {updated}")
    return get_clock_state()


def add_hours_to_clock(hours: int) -> dict[str, str]:
    global CLOCK_CURRENT_TIME
    with CLOCK_LOCK:
        CLOCK_CURRENT_TIME = add_hours_with_rounding(CLOCK_CURRENT_TIME, hours)
        updated = CLOCK_CURRENT_TIME
    console_print(f"clock advanced by {hours} hour(s) to {updated}")
    return get_clock_state()


@app.route("/")
def index() -> Any:
    return redirect(url_for("message_page"))


@app.route("/config", methods=["GET", "POST"])
def config_page() -> Any:
    if request.method == "POST":
        new_config = {
            "num_symbols": request.form.get("num_symbols", DEFAULT_CONFIG["num_symbols"]),
            "default_rotation_speed": request.form.get(
                "default_rotation_speed", DEFAULT_CONFIG["default_rotation_speed"]
            ),
            "i2c_device": request.form.get("i2c_device", DEFAULT_CONFIG["i2c_device"]),
            "log_line_limit": request.form.get("log_line_limit", DEFAULT_CONFIG["log_line_limit"]),
            "default_prop_clock_time": request.form.get(
                "default_prop_clock_time", DEFAULT_CONFIG["default_prop_clock_time"]
            ),
        }
        apply_config(new_config)
        initialize_i2c_scan()
        flash("Configuration saved and reloaded.")
        return redirect(url_for("config_page"))

    return render_template("config.html", config=CONFIG)


@app.route("/message", methods=["GET", "POST"])
def message_page() -> Any:
    preview = ""
    alignment = "left"

    if request.method == "POST":
        action = request.form.get("action", "send")
        if action == "clean":
            clean_message = " " * 10
            send_message_to_display(clean_message)
            console_print("clean display command sent")
            preview = clean_message
            flash("Clean display command sent.")
            return render_template("message.html", config=CONFIG, preview=preview, alignment=alignment)

        raw_text = request.form.get("message", "")
        alignment = request.form.get("alignment", "left")
        if alignment not in {"left", "center", "right"}:
            alignment = "left"

        speed_text = request.form.get("speed", "").strip()
        speed_value = None
        if speed_text:
            try:
                speed_value = max(1, int(speed_text))
            except ValueError:
                flash("Invalid speed value. Using default speed from config.")

        sanitized = sanitize_message(raw_text)
        preview = align_text(sanitized, int(CONFIG["num_symbols"]), alignment)
        console_print(f"received message: {raw_text}")
        send_message_to_display(preview, speed_value)
        flash("Message sent to display.")

    return render_template("message.html", config=CONFIG, preview=preview, alignment=alignment)


@app.route("/logs")
def logs_page() -> Any:
    with LOG_LOCK:
        log_lines = list(LOG_LINES)
    return render_template("logs.html", log_lines=log_lines)


@app.route("/prop-clock")
def prop_clock_page() -> Any:
    return render_template("prop_clock.html", clock=get_clock_state())


@app.post("/api/clock/set-start")
def api_set_start() -> Any:
    payload = request.get_json(silent=True) or {}
    time_text = str(payload.get("time", "")).strip()
    if not validate_time_24h(time_text):
        return jsonify({"error": "Invalid time format. Use HH:MM."}), 400
    clock_state = set_clock_start(time_text)
    return jsonify(clock_state)


@app.post("/api/clock/reset")
def api_reset_clock() -> Any:
    return jsonify(reset_clock())


@app.post("/api/clock/add-minutes")
def api_add_minutes() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        minutes = int(payload.get("minutes", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Allowed minute values are 5, 10, or 30."}), 400
    if minutes not in {5, 10, 30}:
        return jsonify({"error": "Allowed minute values are 5, 10, or 30."}), 400
    return jsonify(add_minutes_to_clock(minutes))


@app.post("/api/clock/add-hours")
def api_add_hours() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        hours = int(payload.get("hours", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Allowed hour values are 1 or 2."}), 400
    if hours not in {1, 2}:
        return jsonify({"error": "Allowed hour values are 1 or 2."}), 400
    return jsonify(add_hours_to_clock(hours))


@app.get("/api/logs")
def api_logs() -> Any:
    with LOG_LOCK:
        return jsonify({"lines": list(LOG_LINES)})


def main() -> None:
    global CONFIG
    CONFIG = load_config()
    set_log_limit(int(CONFIG["log_line_limit"]))
    initialize_clock_state()
    console_print("application startup")
    initialize_i2c_scan()
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
