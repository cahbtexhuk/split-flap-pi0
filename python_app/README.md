# Python App

Flask web application for controlling a split-flap display from a browser UI and clock API calls.

## Features

- Config page:
	- Number of display symbols (default: 10)
	- Default rotation speed
	- I2C device index
	- Log line limit
	- Default prop clock start time (HH:MM, 24-hour)
- Message page:
	- Send text with left/center/right alignment
	- Optional speed override
	- Clean button sends 10 spaces
- Console log page:
	- Timestamped in-app logs from startup onward
	- In-memory history limited by configurable log line count
- Prop clock page:
	- Override start time
	- Reset to start time
	- Add 5/10/30 minutes
	- Add 1/2 hours with custom rounding behavior

## Install

From this folder:

```bash
pip install -r requirements.txt
```

## Run

From this folder:

```bash
python main.py
```

Run with I2C disabled (simulation mode):

```bash
python main.py --disable-i2c
```

Alias:

```bash
python main.py --no-i2c
```

Mode behavior:

- No flag: real I2C mode
- `--disable-i2c` or `--no-i2c`: I2C is disabled and calls are simulated as successful

Open:

http://localhost:5000

## API (clock controls)

All API routes are POST and return JSON.

- `/api/clock/set-start`
	- Body: `{"time": "HH:MM"}`
- `/api/clock/reset`
	- Body: `{}`
- `/api/clock/add-minutes`
	- Body: `{"minutes": 5}` (allowed: 5, 10, 30)
- `/api/clock/add-hours`
	- Body: `{"hours": 1}` (allowed: 1, 2)

Response shape:

```json
{
	"start_time": "12:00",
	"current_time": "12:05"
}
```

## Notes

- Display output is routed through `send_message_to_display(message, speed=None)` as a placeholder for hardware logic.
- On startup and after config save, the app scans I2C addresses 1..`num_symbols` and logs pass/fail checks.
