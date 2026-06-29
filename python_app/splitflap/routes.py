from __future__ import annotations

from typing import Any

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from . import data, hardware


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index() -> Any:
        return redirect(url_for("message_page"))

    @app.route("/config", methods=["GET", "POST"])
    def config_page() -> Any:
        if request.method == "POST":
            new_config = {
                "num_symbols": request.form.get("num_symbols", data.DEFAULT_CONFIG["num_symbols"]),
                "default_rotation_speed": request.form.get(
                    "default_rotation_speed", data.DEFAULT_CONFIG["default_rotation_speed"]
                ),
                "i2c_device": request.form.get("i2c_device", data.DEFAULT_CONFIG["i2c_device"]),
                "log_line_limit": request.form.get("log_line_limit", data.DEFAULT_CONFIG["log_line_limit"]),
                "default_prop_clock_time": request.form.get(
                    "default_prop_clock_time", data.DEFAULT_CONFIG["default_prop_clock_time"]
                ),
            }
            data.apply_config(new_config)
            hardware.initialize_i2c_scan(data.get_config(), data.console_print)
            flash("Configuration saved and reloaded.")
            return redirect(url_for("config_page"))

        return render_template("config.html", config=data.get_config())

    @app.post("/config/restart")
    def config_restart() -> Any:
        data.startup_initialize()
        hardware.initialize_i2c_scan(data.get_config(), data.console_print)
        flash("Initialisation complete — I2C scan finished.")
        return redirect(url_for("config_page"))

    @app.route("/message", methods=["GET", "POST"])
    def message_page() -> Any:
        preview = ""
        alignment = "left"

        if request.method == "POST":
            action = request.form.get("action", "send")
            if action == "clean":
                clean_message = " " * 10
                hardware.send_message_to_display(clean_message, None, data.get_config(), data.console_print)
                data.console_print("clean display command sent")
                preview = clean_message
                flash("Clean display command sent.")
                return render_template(
                    "message.html",
                    config=data.get_config(),
                    preview=preview,
                    alignment=alignment,
                )

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

            cfg = data.get_config()
            sanitized = data.sanitize_message(raw_text)
            preview = data.align_text(sanitized, int(cfg["num_symbols"]), alignment)
            data.console_print(f"received message: {raw_text}")
            hardware.send_message_to_display(preview, speed_value, cfg, data.console_print)
            flash("Message sent to display.")

        return render_template("message.html", config=data.get_config(), preview=preview, alignment=alignment)

    @app.route("/logs")
    def logs_page() -> Any:
        return render_template("logs.html", log_lines=data.get_log_lines())

    @app.route("/prop-clock")
    def prop_clock_page() -> Any:
        return render_template("prop_clock.html", clock=data.get_clock_state())

    @app.post("/api/clock/set-start")
    def api_set_start() -> Any:
        payload = request.get_json(silent=True) or {}
        time_text = str(payload.get("time", "")).strip()
        if not data.validate_time_24h(time_text):
            return jsonify({"error": "Invalid time format. Use HH:MM."}), 400
        clock_state = data.set_clock_start(time_text)
        return jsonify(clock_state)

    @app.post("/api/clock/reset")
    def api_reset_clock() -> Any:
        return jsonify(data.reset_clock())

    @app.post("/api/clock/add-minutes")
    def api_add_minutes() -> Any:
        payload = request.get_json(silent=True) or {}
        try:
            minutes = int(payload.get("minutes", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Allowed minute values are 5, 10, or 30."}), 400
        if minutes not in {5, 10, 30}:
            return jsonify({"error": "Allowed minute values are 5, 10, or 30."}), 400
        return jsonify(data.add_minutes_to_clock(minutes))

    @app.post("/api/clock/add-hours")
    def api_add_hours() -> Any:
        payload = request.get_json(silent=True) or {}
        try:
            hours = int(payload.get("hours", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Allowed hour values are 1 or 2."}), 400
        if hours not in {1, 2}:
            return jsonify({"error": "Allowed hour values are 1 or 2."}), 400
        return jsonify(data.add_hours_to_clock(hours))

    @app.get("/api/logs")
    def api_logs() -> Any:
        return jsonify({"lines": data.get_log_lines()})
