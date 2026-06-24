from __future__ import annotations

import argparse

from flask import Flask

from splitflap import data, hardware
from splitflap.routes import register_routes


app = Flask(__name__)
app.secret_key = "split-flap-dev-secret"
register_routes(app)


def _display_sender(message: str, speed: int | None) -> None:
    hardware.send_message_to_display(message, speed, data.get_config(), data.console_print)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split-flap web controller")
    parser.add_argument(
        "--disable-i2c",
        "--no-i2c",
        action="store_true",
        help="Disable real I2C access and simulate successful hardware calls.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hardware.SIMULATE_I2C = bool(args.disable_i2c)

    data.startup_initialize()
    data.set_display_sender(_display_sender)
    data.console_print("application startup")
    if hardware.SIMULATE_I2C:
        data.console_print("[SIMULATE] i2c simulation mode active - no hardware will be accessed")
    else:
        data.console_print("i2c hardware mode active")
    hardware.initialize_i2c_scan(data.get_config(), data.console_print)
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
