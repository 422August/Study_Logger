# Study Logger

A lightweight command-line study tracker written in Python.

Study Logger is designed to keep study tracking simple while still providing useful timing, focus, record management, and analysis features. It stores study records locally and provides stopwatch, countdown, and Pomodoro modes without requiring a database or external service.

## Features

### Study Timers

Study Logger provides three timing modes:

* **Stopwatch** — Start a study session and stop it whenever you finish.
* **Countdown** — Study for a predefined or custom amount of time.
* **Pomodoro** — Alternate automatically between focused study sessions and breaks.

Completed sessions are automatically added to your study records.

### Subjects

Study sessions are organized into eight predefined subjects:

* Chinese
* English
* Mathematics
* Physics
* Chemistry
* Biology
* Earth Science
* Social Sciences

Using predefined subjects keeps statistics consistent and prevents duplicate categories caused by different spellings.

### Pomodoro Timer

The built-in Pomodoro timer supports configurable:

* Work duration
* Short break duration
* Long break duration
* Number of rounds

Only work sessions are counted toward study time. Breaks are excluded from study statistics.

### Manual Logging

Study sessions that were completed without running a timer can be added manually.

Manual records support:

* Subject selection
* Duration
* Date
* Optional notes

### Record Management

Stored records can be viewed and managed directly from the application.

Available operations include:

* View recent records
* Search by subject
* Search by date
* Search through notes
* Edit existing records
* Delete records

### Study Analysis

Analysis is separated into multiple pages to keep the interface readable.

**Overview** displays:

* Study time today
* Daily study goal
* Daily goal progress
* Study time yesterday at the same time of day
* Difference between today and yesterday
* Seven-day study total
* Seven-day daily average
* Current study streak
* Total accumulated study time
* Total number of sessions

**Subjects** displays study time for each subject across different periods.

**Trends** provides recent study activity, including seven-day and longer-term statistics.

### Yesterday Comparison

Study Logger compares today's accumulated study time with yesterday's study time at approximately the same point in the day.

For example, if the current time is 9:30 PM, today's progress is compared with yesterday's progress up to 9:30 PM rather than with the entire previous day.

Timer-based records containing start and end times can be truncated to the comparison time for more accurate statistics.

Manual records do not contain a specific start time and therefore cannot always be compared with the same level of precision.

### Daily Goal

A configurable daily study goal is displayed directly on the main screen.

Example:

```text
=== Study Logger ===
Today 2h 10m / 3h 0m
[#################-------] 72%
Yesterday now 1h 35m · +35m

1. Study
2. Manual Log
3. Records
4. Analysis
5. Settings
0. Exit
```

### Windows Input Lock

Study Logger includes an optional Windows input-lock feature intended for focused countdown and Pomodoro sessions.

When successfully enabled, it uses the Windows `BlockInput` API to temporarily block physical keyboard and mouse input.

This feature:

* Is available only on Windows.
* Requires elevated administrator privileges.
* Is disabled by default.
* Is intended for fixed-duration sessions.
* May be unavailable when Study Logger is running without sufficient privileges.

Windows provides system-level recovery mechanisms such as `Ctrl+Alt+Delete`.

Use this feature carefully. The application should not be terminated forcibly while an input lock is active.

## Requirements

* Python 3.10 or newer
* Windows, Linux, or macOS for general study tracking
* Windows for the optional input-lock feature

The core application uses Python's standard library and does not require third-party Python packages.

## Installation

Clone the repository:

```bash
git clone https://github.com/422August/Study_Logger/
cd study_logger
```

Run the application:

```bash
python main.py
```

On Windows, depending on your Python installation, you may also use:

```powershell
py main.py
```

## Data Storage

Study records are stored locally in:

```text
study_records.csv
```

Application settings are stored in:

```text
study_settings.json
```

No study data is intentionally uploaded to an external server by Study Logger.

It is recommended to periodically back up `study_records.csv` if the data is important to you.

## Record Format

Study records contain fields such as:

```text
date
start_time
end_time
subject
duration_minutes
type
notes
```

This CSV-based format allows study data to be opened and processed using spreadsheet software or other analysis tools.

## Configuration

Settings can be changed from the application's Settings menu.

Configurable options include:

* Daily study goal
* Pomodoro work duration
* Pomodoro short break duration
* Pomodoro long break duration
* Pomodoro rounds
* Windows input lock

Settings are persisted between application launches.

## Project Structure

A typical installation contains:

```text
study_logger/
├── main.py
├── README.md
├── LICENSE
├── study_records.csv
└── study_settings.json
```

The data and settings files may be created automatically when the application is first started.

## Privacy

Study Logger is designed as a local application.

Study records, subjects, session durations, and notes are stored locally in CSV and JSON files. Users should avoid placing sensitive information in study notes when the files are stored in shared or synchronized directories.

## Known Limitations

The Windows input-lock feature depends on operating-system permissions and may fail when the application is not running with sufficient privileges.

Manual study records do not contain exact start and end times, so time-of-day comparisons involving manual records may be less precise than comparisons involving timer-based sessions.

Terminal appearance and certain behaviors may vary depending on the operating system and terminal emulator.

## Contributing

Contributions, bug reports, and suggestions are welcome.

When contributing code, please keep the interface simple and avoid unnecessary dependencies where possible.

Python code should be formatted with [Black](https://github.com/psf/black).

## License

This project is free software licensed under the **GNU General Public License version 3 (GPL-3.0)**.

See the `LICENSE` file for the complete license text.

For more information about the GNU General Public License version 3, visit the GNU Project website.
