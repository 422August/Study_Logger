import csv
import ctypes
import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_PATH = os.path.join(BASE_DIR, "study_records.csv")
SETTINGS_PATH = os.path.join(BASE_DIR, "study_settings.json")
FIELDNAMES = [
    "date",
    "start_time",
    "end_time",
    "subject",
    "duration_minutes",
    "type",
    "notes",
]
SUBJECTS = (
    "Chinese",
    "English",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Earth Science",
    "Science (Question)",
    "Social Sciences",
)
DEFAULT_SETTINGS = {
    "daily_goal_minutes": 180,
    "pomodoro_work_minutes": 25,
    "pomodoro_short_break_minutes": 5,
    "pomodoro_long_break_minutes": 15,
    "pomodoro_rounds": 4,
    "windows_input_lock": False,
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="Press Enter to continue..."):
    input(f"\n{message}")


def print_header(title):
    print(f"=== {title} ===")


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_minutes(minutes):
    total = max(0, int(round(float(minutes))))
    hours, mins = divmod(total, 60)
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def format_clock(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def progress_bar(current, target, width=24):
    if target <= 0:
        return "[" + "-" * width + "] 0%"
    ratio = current / target
    filled = min(width, int(min(ratio, 1.0) * width))
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {ratio * 100:.0f}%"


def ensure_data_file():
    if os.path.exists(FILE_PATH):
        return
    with open(FILE_PATH, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()


def load_records():
    ensure_data_file()
    with open(FILE_PATH, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_records(records):
    temp_path = f"{FILE_PATH}.tmp"
    with open(temp_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    os.replace(temp_path, FILE_PATH)


def append_record(record):
    ensure_data_file()

    # Make sure the existing file ends with a newline.
    if os.path.getsize(FILE_PATH) > 0:
        with open(FILE_PATH, "rb") as file:
            file.seek(-1, os.SEEK_END)
            last_byte = file.read(1)

        if last_byte not in (b"\n", b"\r"):
            with open(FILE_PATH, "ab") as file:
                file.write(b"\n")

    with open(FILE_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writerow(record)


def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    if not os.path.exists(SETTINGS_PATH):
        save_settings(settings)
        return settings
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
            loaded = json.load(file)
        if isinstance(loaded, dict):
            settings.update(loaded)
    except (OSError, json.JSONDecodeError):
        save_settings(settings)
    return settings


def save_settings(settings):
    temp_path = f"{SETTINGS_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)
    os.replace(temp_path, SETTINGS_PATH)


def choose_subject():
    while True:
        clear_screen()
        print_header("Subject")
        for index, subject in enumerate(SUBJECTS, start=1):
            print(f"{index}. {subject}")
        print("0. Back")
        choice = input("\nSelect: ").strip()
        if choice == "0":
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(SUBJECTS):
                return SUBJECTS[index]
        except ValueError:
            pass
        print("Invalid selection.")
        time.sleep(0.8)


def ask_positive_float(prompt, default=None):
    value = input(prompt).strip()
    if not value and default is not None:
        return float(default)
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number > 0 else None


def ask_positive_int(prompt, default=None):
    value = input(prompt).strip()
    if not value and default is not None:
        return int(default)
    try:
        number = int(value)
    except ValueError:
        return None
    return number if number > 0 else None




def parse_clock_text(value):
    value = value.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass
    return None


def combine_session_datetimes(record_date, start_time, end_time):
    start_dt = datetime.combine(record_date.date(), start_time)
    end_dt = datetime.combine(record_date.date(), end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt

def make_record(subject, start_dt, end_dt, minutes, record_type, notes=""):
    return {
        "date": start_dt.strftime("%Y-%m-%d"),
        "start_time": start_dt.strftime("%H:%M:%S"),
        "end_time": end_dt.strftime("%H:%M:%S"),
        "subject": subject,
        "duration_minutes": round(minutes, 1),
        "type": record_type,
        "notes": notes.strip(),
    }


def ring():
    print("\a", end="", flush=True)


class WindowsInputLock:
    def __init__(self):
        self.release_event = threading.Event()
        self.thread = None
        self.active = False

    def start(self, timeout_seconds):
        if os.name != "nt":
            return False
        ready = threading.Event()
        result = {"active": False}

        def worker():
            try:
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                blocked = bool(user32.BlockInput(True))
            except (AttributeError, OSError):
                blocked = False
            result["active"] = blocked
            self.active = blocked
            ready.set()
            if not blocked:
                return
            try:
                self.release_event.wait(timeout=max(1, timeout_seconds))
            finally:
                user32.BlockInput(False)
                self.active = False

        self.release_event.clear()
        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()
        ready.wait(timeout=2)
        return result["active"]

    def release(self):
        self.release_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.active = False


def run_fixed_timer(seconds, title, subject=None, use_input_lock=False):
    clear_screen()
    print_header(title)
    if subject:
        print(subject)
    print()
    input_lock = WindowsInputLock()
    lock_active = False
    if use_input_lock:
        print("Input lock requested. Starting in 3 seconds...")
        time.sleep(3)
        lock_active = input_lock.start(seconds + 10)
        clear_screen()
        print_header(title)
        if subject:
            print(subject)
        if lock_active:
            print("Windows input lock: ON")
        else:
            print("Windows input lock unavailable; Ctrl+C can stop early.")
    elif os.name == "nt":
        print("Ctrl+C to stop early.")
    else:
        print("Ctrl+C to stop early.")
    started = time.monotonic()
    completed = False
    try:
        while True:
            elapsed = time.monotonic() - started
            remaining = seconds - elapsed
            if remaining <= 0:
                completed = True
                remaining = 0
            ratio = min(elapsed / seconds, 1.0) if seconds else 1.0
            width = 24
            filled = int(ratio * width)
            bar = "#" * filled + "-" * (width - filled)
            print(
                f"\r{format_clock(remaining)} [{bar}] {ratio * 100:5.1f}%",
                end="",
                flush=True,
            )
            if completed:
                break
            time.sleep(0.2)
    except KeyboardInterrupt:
        completed = False
    finally:
        elapsed = min(time.monotonic() - started, seconds)
        input_lock.release()
        print()
    return elapsed, completed, lock_active


def live_timer():
    subject = choose_subject()
    if subject is None:
        return
    clear_screen()
    print_header("Stopwatch")
    print(subject)
    notes = input("Notes (optional): ").strip()
    input("Press Enter to start...")
    clear_screen()
    print_header("Stopwatch")
    print(subject)
    print("Press Enter to stop.")
    started_dt = datetime.now()
    started = time.monotonic()
    stop_event = threading.Event()

    def display():
        while not stop_event.is_set():
            elapsed = time.monotonic() - started
            print(f"\r{format_clock(elapsed)}", end="", flush=True)
            time.sleep(0.2)

    thread = threading.Thread(target=display, daemon=True)
    thread.start()
    try:
        input()
    except KeyboardInterrupt:
        pass
    stop_event.set()
    thread.join()
    ended_dt = datetime.now()
    elapsed_seconds = time.monotonic() - started
    clear_screen()
    print_header("Saved")
    append_record(
        make_record(
            subject,
            started_dt,
            ended_dt,
            elapsed_seconds / 60,
            "Stopwatch",
            notes,
        )
    )
    duration_text = format_minutes(elapsed_seconds / 60)
    print(f"{subject}  {duration_text}")
    pause()


def countdown_timer():
    subject = choose_subject()
    if subject is None:
        return
    clear_screen()
    print_header("Countdown")
    print("1. 25m")
    print("2. 50m")
    print("3. 90m")
    print("4. Custom")
    print("0. Back")
    choice = input("\nSelect: ").strip()
    presets = {"1": 25, "2": 50, "3": 90}
    if choice == "0":
        return
    if choice in presets:
        minutes = float(presets[choice])
    elif choice == "4":
        minutes = ask_positive_float("Minutes: ")
        if minutes is None:
            print("Invalid duration.")
            pause()
            return
    else:
        return
    notes = input("Notes (optional): ").strip()
    settings = load_settings()
    use_lock = bool(settings["windows_input_lock"])
    start_dt = datetime.now()
    elapsed, completed, _ = run_fixed_timer(
        int(minutes * 60), "Countdown", subject, use_lock
    )
    end_dt = datetime.now()
    if completed:
        ring()
        append_record(
            make_record(
                subject,
                start_dt,
                end_dt,
                elapsed / 60,
                "Countdown",
                notes,
            )
        )
        clear_screen()
        print_header("Saved")
        duration_text = format_minutes(elapsed / 60)
        print(f"{subject}  {duration_text}")
        pause()
        return
    clear_screen()
    print_header("Stopped")
    elapsed_text = format_minutes(elapsed / 60)
    print(f"Elapsed: {elapsed_text}")
    if elapsed >= 60 and input("Save partial session? [Y/n]: ").strip().lower() != "n":
        append_record(
            make_record(
                subject,
                start_dt,
                end_dt,
                elapsed / 60,
                "Countdown (Partial)",
                notes,
            )
        )
        print("Saved.")
    pause()


def pomodoro_timer():
    subject = choose_subject()
    if subject is None:
        return
    settings = load_settings()
    clear_screen()
    print_header("Pomodoro")
    work_minutes = settings["pomodoro_work_minutes"]
    short_break_minutes = settings["pomodoro_short_break_minutes"]
    long_break_minutes = settings["pomodoro_long_break_minutes"]
    default_rounds = settings["pomodoro_rounds"]

    print(
        f"{work_minutes}m work / "
        f"{short_break_minutes}m break / "
        f"{long_break_minutes}m long break"
    )

    rounds_prompt = f"Rounds [{default_rounds}]: "
    rounds = ask_positive_int(rounds_prompt, default_rounds)
    if rounds is None:
        print("Invalid rounds.")
        pause()
        return
    notes = input("Notes (optional): ").strip()
    work_seconds = int(settings["pomodoro_work_minutes"] * 60)
    short_break_seconds = int(settings["pomodoro_short_break_minutes"] * 60)
    long_break_seconds = int(settings["pomodoro_long_break_minutes"] * 60)
    use_lock = bool(settings["windows_input_lock"])
    completed_rounds = 0
    for round_number in range(1, rounds + 1):
        start_dt = datetime.now()
        elapsed, completed, _ = run_fixed_timer(
            work_seconds,
            f"Pomodoro {round_number}/{rounds} · Work",
            subject,
            use_lock,
        )
        end_dt = datetime.now()
        if completed:
            append_record(
                make_record(
                    subject,
                    start_dt,
                    end_dt,
                    elapsed / 60,
                    "Pomodoro",
                    notes,
                )
            )
            completed_rounds += 1
            ring()
        else:
            clear_screen()
            print_header("Pomodoro Stopped")
            elapsed_text = format_minutes(elapsed / 60)
            print(f"Elapsed: {elapsed_text}")
            if (
                elapsed >= 60
                and input("Save partial work? [Y/n]: ").strip().lower() != "n"
            ):
                append_record(
                    make_record(
                        subject,
                        start_dt,
                        end_dt,
                        elapsed / 60,
                        "Pomodoro (Partial)",
                        notes,
                    )
                )
            pause()
            return
        if round_number == rounds:
            break
        is_long_break = round_number % settings["pomodoro_rounds"] == 0
        break_seconds = long_break_seconds if is_long_break else short_break_seconds
        break_name = "Long Break" if is_long_break else "Break"
        _, break_completed, _ = run_fixed_timer(
            break_seconds,
            f"Pomodoro {round_number}/{rounds} · {break_name}",
            use_input_lock=False,
        )
        ring()
        if not break_completed:
            clear_screen()
            print_header("Break Skipped")
            time.sleep(0.8)
    clear_screen()
    print_header("Pomodoro Complete")
    print(f"{subject}  {completed_rounds}/{rounds} rounds")
    study_minutes = completed_rounds * work_seconds / 60
    study_time_text = format_minutes(study_minutes)
    print(f"Study time: {study_time_text}")
    pause()


def study_menu():
    while True:
        clear_screen()
        print_header("Study")
        print("1. Stopwatch")
        print("2. Countdown")
        print("3. Pomodoro")
        print("0. Back")
        choice = input("\nSelect: ").strip()
        if choice == "1":
            live_timer()
        elif choice == "2":
            countdown_timer()
        elif choice == "3":
            pomodoro_timer()
        elif choice == "0":
            return


def manual_log():
    subject = choose_subject()
    if subject is None:
        return

    clear_screen()
    print_header("Manual Log")
    print(subject)

    now = datetime.now()
    date_text = input("Date YYYY-MM-DD [today]: ").strip()
    if date_text:
        try:
            record_date = datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            print("Invalid date.")
            pause()
            return
    else:
        record_date = now

    default_time = now.strftime("%H:%M")
    start_text = input(f"Start time HH:MM [{default_time}]: ").strip() or default_time
    start_time = parse_clock_text(start_text)
    if start_time is None:
        print("Invalid start time.")
        pause()
        return

    end_text = input(f"End time HH:MM [{default_time}]: ").strip() or default_time
    end_time = parse_clock_text(end_text)
    if end_time is None:
        print("Invalid end time.")
        pause()
        return

    start_dt, end_dt = combine_session_datetimes(record_date, start_time, end_time)
    minutes = (end_dt - start_dt).total_seconds() / 60
    if minutes <= 0:
        print("Duration must be greater than 0 minutes.")
        pause()
        return

    notes = input("Notes (optional): ").strip()
    append_record(make_record(subject, start_dt, end_dt, minutes, "Manual", notes))

    clear_screen()
    print_header("Saved")
    print(f"{subject}  {format_minutes(minutes)}")
    print(f"{start_dt.strftime('%H:%M')} -> {end_dt.strftime('%H:%M')}")
    pause()


def display_record(number, row):
    duration = safe_float(row.get("duration_minutes"))
    date_text = row.get("date", "")
    start_text = row.get("start_time", "")
    end_text = row.get("end_time", "")
    subject_text = row.get("subject", "")
    type_text = row.get("type", "")
    duration_text = format_minutes(duration)

    if start_text and end_text and start_text != "N/A" and end_text != "N/A":
        time_text = f"{start_text[:5]}-{end_text[:5]}"
    else:
        time_text = "--:-----:--"

    print(
        f"{number:>2}. {date_text} {time_text:<11} "
        f"{subject_text:<15} {duration_text:>7}  {type_text}"
    )
    notes = row.get("notes", "").strip()
    if notes:
        print(f"    {notes}")


def recent_record_indices(records, limit=20):
    start = len(records) - 1
    stop = max(-1, len(records) - limit - 1)
    return list(range(start, stop, -1))


def view_records(records=None):
    clear_screen()
    print_header("Records")
    records = load_records() if records is None else records
    if not records:
        print("No records.")
        pause()
        return
    indices = recent_record_indices(records)
    for number, record_index in enumerate(indices, start=1):
        display_record(number, records[record_index])
    if len(records) > len(indices):
        print(f"\nShowing latest {len(indices)} of {len(records)} records.")
    pause()


def search_records():
    records = load_records()
    if not records:
        view_records(records)
        return
    clear_screen()
    print_header("Search")
    print("1. Subject")
    print("2. Date")
    print("3. Notes")
    print("0. Back")
    choice = input("\nSelect: ").strip()
    if choice == "0":
        return
    if choice == "1":
        subject = choose_subject()
        if subject is None:
            return
        matches = [row for row in records if row.get("subject") == subject]
    elif choice == "2":
        query = input("Date YYYY-MM-DD: ").strip()
        matches = [row for row in records if row.get("date") == query]
    elif choice == "3":
        query = input("Keyword: ").strip().lower()
        matches = [
            row for row in records if query in row.get("notes", "").lower()
        ]
    else:
        return
    clear_screen()
    print_header("Search Results")
    if not matches:
        print("No matches.")
    else:
        for number, row in enumerate(reversed(matches[-20:]), start=1):
            display_record(number, row)
    pause()


def select_recent_record(records, title):
    if not records:
        return None
    clear_screen()
    print_header(title)
    indices = recent_record_indices(records)
    for number, record_index in enumerate(indices, start=1):
        display_record(number, records[record_index])
    choice = input("\nRecord number [0 = back]: ").strip()
    if choice == "0":
        return None
    try:
        menu_index = int(choice) - 1
        if 0 <= menu_index < len(indices):
            return indices[menu_index]
    except ValueError:
        pass
    return None


def edit_record():
    records = load_records()
    index = select_recent_record(records, "Edit")
    if index is None:
        return

    record = records[index]
    clear_screen()
    print_header("Edit")
    print(f"Subject: {record['subject']}")
    print(f"Date: {record.get('date', '')}")
    print(f"Start: {record.get('start_time', '')}")
    print(f"End: {record.get('end_time', '')}")
    print(f"Duration: {record['duration_minutes']}m")
    print(f"Notes: {record['notes']}")
    print("\n1. Subject")
    print("2. Date")
    print("3. Start time")
    print("4. End time")
    print("5. Notes")
    print("0. Back")
    choice = input("\nSelect: ").strip()

    if choice == "1":
        subject = choose_subject()
        if subject is None:
            return
        record["subject"] = subject

    elif choice == "2":
        current = record.get("date", "")
        date_text = input(f"Date YYYY-MM-DD [{current}]: ").strip() or current
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            print("Invalid date.")
            pause()
            return
        record["date"] = date_text

    elif choice in ("3", "4"):
        field = "start_time" if choice == "3" else "end_time"
        label = "Start time" if choice == "3" else "End time"
        current = record.get(field, "")
        default_display = current[:5] if current and current != "N/A" else datetime.now().strftime("%H:%M")
        value = input(f"{label} HH:MM [{default_display}]: ").strip() or default_display
        parsed = parse_clock_text(value)
        if parsed is None:
            print("Invalid time.")
            pause()
            return
        record[field] = parsed.strftime("%H:%M:%S")

    elif choice == "5":
        record["notes"] = input("Notes: ").strip()

    else:
        return

    start_text = record.get("start_time", "")
    end_text = record.get("end_time", "")
    if start_text != "N/A" and end_text != "N/A":
        try:
            record_date = datetime.strptime(record["date"], "%Y-%m-%d")
            start_time = datetime.strptime(start_text, "%H:%M:%S").time()
            end_time = datetime.strptime(end_text, "%H:%M:%S").time()
            start_dt, end_dt = combine_session_datetimes(record_date, start_time, end_time)
            minutes = (end_dt - start_dt).total_seconds() / 60
            if minutes <= 0:
                print("Duration must be greater than 0 minutes.")
                pause()
                return
            record["duration_minutes"] = round(minutes, 1)
        except ValueError:
            pass

    save_records(records)
    print("Saved.")
    pause()


def delete_record():
    records = load_records()
    index = select_recent_record(records, "Delete")
    if index is None:
        return
    record = records[index]
    clear_screen()
    print_header("Delete")
    display_record(1, record)
    if input("\nDelete? [y/N]: ").strip().lower() != "y":
        return
    records.pop(index)
    save_records(records)
    print("Deleted.")
    pause()


def records_menu():
    while True:
        clear_screen()
        print_header("Records")
        print("1. Recent")
        print("2. Search")
        print("3. Edit")
        print("4. Delete")
        print("0. Back")
        choice = input("\nSelect: ").strip()
        if choice == "1":
            view_records()
        elif choice == "2":
            search_records()
        elif choice == "3":
            edit_record()
        elif choice == "4":
            delete_record()
        elif choice == "0":
            return


def build_statistics(records):
    subject_totals = defaultdict(float)
    date_totals = defaultdict(float)
    total_minutes = 0.0
    sessions = 0
    for row in records:
        minutes = safe_float(row.get("duration_minutes"))
        try:
            day = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        subject = row.get("subject", "Unknown")
        subject_totals[subject] += minutes
        date_totals[day] += minutes
        total_minutes += minutes
        sessions += 1
    return subject_totals, date_totals, total_minutes, sessions


def calculate_streak(date_totals):
    today = datetime.now().date()
    cursor = today if date_totals.get(today, 0) > 0 else today - timedelta(days=1)
    streak = 0
    while date_totals.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def format_signed_minutes(minutes):
    if abs(minutes) < 0.5:
        return "0m"
    sign = "+" if minutes > 0 else "-"
    return f"{sign}{format_minutes(abs(minutes))}"


def record_minutes_until(row, day, cutoff):
    minutes = safe_float(row.get("duration_minutes"))
    if minutes <= 0:
        return 0.0

    start_text = row.get("start_time", "")
    end_text = row.get("end_time", "")
    if start_text == "N/A" or end_text == "N/A":
        return minutes

    try:
        start_time = datetime.strptime(start_text, "%H:%M:%S").time()
        end_time = datetime.strptime(end_text, "%H:%M:%S").time()
    except ValueError:
        return minutes

    start_dt = datetime.combine(day, start_time)
    end_dt = datetime.combine(day, end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    if start_dt >= cutoff:
        return 0.0

    counted_end = min(end_dt, cutoff)
    elapsed_minutes = max(0.0, (counted_end - start_dt).total_seconds() / 60)
    return min(minutes, elapsed_minutes)


def study_minutes_until(records, day, cutoff):
    date_text = day.strftime("%Y-%m-%d")
    total = 0.0
    for row in records:
        if row.get("date") != date_text:
            continue
        total += record_minutes_until(row, day, cutoff)
    return total


def same_time_comparison(records):
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    yesterday_cutoff = datetime.combine(yesterday, now.time())
    today_minutes = study_minutes_until(records, today, now)
    yesterday_minutes = study_minutes_until(records, yesterday, yesterday_cutoff)
    difference = today_minutes - yesterday_minutes
    return today_minutes, yesterday_minutes, difference


def analysis_overview(records, settings):
    subject_totals, date_totals, total_minutes, sessions = build_statistics(records)
    today = datetime.now().date()
    today_minutes, yesterday_minutes, difference = same_time_comparison(records)
    seven_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    seven_total = sum(date_totals.get(day, 0) for day in seven_days)
    daily_goal = settings["daily_goal_minutes"]

    clear_screen()
    print_header("Analysis · Overview")
    print(f"Today       {format_minutes(today_minutes)} / {format_minutes(daily_goal)}")
    print(progress_bar(today_minutes, daily_goal))
    print(f"Yesterday   {format_minutes(yesterday_minutes)} at this time")
    print(f"Difference  {format_signed_minutes(difference)}")
    seven_total_text = format_minutes(seven_total)
    seven_average_text = format_minutes(seven_total / 7)
    print(f"7 days      {seven_total_text} · avg {seven_average_text}")
    print(f"Streak      {calculate_streak(date_totals)} day(s)")
    print(f"All time    {format_minutes(total_minutes)} · {sessions} sessions")
    pause()


def analysis_subjects(records):
    subject_totals = defaultdict(float)
    today_totals = defaultdict(float)
    seven_day_totals = defaultdict(float)
    now = datetime.now()
    today = now.date()
    first_day = today - timedelta(days=6)

    for row in records:
        subject = row.get("subject", "Unknown")
        minutes = safe_float(row.get("duration_minutes"))
        try:
            day = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        subject_totals[subject] += minutes
        if day == today:
            today_totals[subject] += minutes
        if first_day <= day <= today:
            seven_day_totals[subject] += minutes

    clear_screen()
    print_header("Analysis · Subjects")
    print(f"{'Subject':<16} {'Today':>7} {'7 days':>8} {'All':>8}")
    print("-" * 43)
    for subject in SUBJECTS:
        today_text = format_minutes(today_totals.get(subject, 0))
        seven_text = format_minutes(seven_day_totals.get(subject, 0))
        all_text = format_minutes(subject_totals.get(subject, 0))
        print(f"{subject:<16} {today_text:>7} {seven_text:>8} {all_text:>8}")
    pause()


def analysis_trends(records):
    _, date_totals, _, _ = build_statistics(records)
    today = datetime.now().date()
    seven_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    thirty_days = [today - timedelta(days=offset) for offset in range(29, -1, -1)]
    seven_total = sum(date_totals.get(day, 0) for day in seven_days)
    thirty_total = sum(date_totals.get(day, 0) for day in thirty_days)
    active_days = sum(1 for day in thirty_days if date_totals.get(day, 0) > 0)

    clear_screen()
    print_header("Analysis · Trends")
    print(f"7-day total   {format_minutes(seven_total)}")
    print(f"7-day average {format_minutes(seven_total / 7)}")
    print(f"30-day total  {format_minutes(thirty_total)}")
    print(f"Active days   {active_days}/30")
    print("\nLast 7 days")
    for day in seven_days:
        minutes = date_totals.get(day, 0)
        blocks = min(20, int(round(minutes / 30)))
        if minutes > 0 and blocks == 0:
            blocks = 1
        day_text = day.strftime("%m-%d")
        minutes_text = format_minutes(minutes)
        print(f"{day_text} {minutes_text:>6}  {'#' * blocks}")
    pause()


def analysis():
    records = load_records()
    if not records:
        clear_screen()
        print_header("Analysis")
        print("No records.")
        pause()
        return

    while True:
        clear_screen()
        print_header("Analysis")
        print("1. Overview")
        print("2. Subjects")
        print("3. Trends")
        print("0. Back")
        choice = input("\nSelect: ").strip()
        if choice == "1":
            analysis_overview(records, load_settings())
        elif choice == "2":
            analysis_subjects(records)
        elif choice == "3":
            analysis_trends(records)
        elif choice == "0":
            return

def edit_daily_goal(settings):
    clear_screen()
    print_header("Daily Goal")
    current_goal_text = format_minutes(settings["daily_goal_minutes"])
    print(f"Current: {current_goal_text}")
    minutes = ask_positive_float("New goal in minutes: ")
    if minutes is None:
        return
    settings["daily_goal_minutes"] = minutes
    save_settings(settings)


def edit_pomodoro(settings):
    clear_screen()
    print_header("Pomodoro Settings")
    current_work = settings["pomodoro_work_minutes"]
    current_short_break = settings["pomodoro_short_break_minutes"]
    current_long_break = settings["pomodoro_long_break_minutes"]
    current_rounds = settings["pomodoro_rounds"]

    work_prompt = f"Work [{current_work}]: "
    short_break_prompt = f"Short break [{current_short_break}]: "
    long_break_prompt = f"Long break [{current_long_break}]: "
    rounds_prompt = f"Rounds [{current_rounds}]: "

    work = ask_positive_int(work_prompt, current_work)
    short_break = ask_positive_int(short_break_prompt, current_short_break)
    long_break = ask_positive_int(long_break_prompt, current_long_break)
    rounds = ask_positive_int(rounds_prompt, current_rounds)
    if None in (work, short_break, long_break, rounds):
        print("Invalid value.")
        pause()
        return
    settings.update(
        {
            "pomodoro_work_minutes": work,
            "pomodoro_short_break_minutes": short_break,
            "pomodoro_long_break_minutes": long_break,
            "pomodoro_rounds": rounds,
        }
    )
    save_settings(settings)


def toggle_input_lock(settings):
    clear_screen()
    print_header("Windows Input Lock")
    if os.name != "nt":
        print("This option is only available on Windows.")
        pause()
        return
    current = bool(settings["windows_input_lock"])
    current_text = "ON" if current else "OFF"
    print(f"Current: {current_text}")
    print("Applies only to fixed Countdown/Pomodoro work periods.")
    print("While locked, normal mouse and keyboard input is blocked.")
    print("Windows can release it with Ctrl+Alt+Del if necessary.")
    if input("\nToggle? [y/N]: ").strip().lower() != "y":
        return
    settings["windows_input_lock"] = not current
    save_settings(settings)


def settings_menu():
    while True:
        settings = load_settings()
        clear_screen()
        print_header("Settings")
        goal_text = format_minutes(settings["daily_goal_minutes"])
        print(f"1. Daily goal       {goal_text}")
        work_minutes = settings["pomodoro_work_minutes"]
        short_break_minutes = settings["pomodoro_short_break_minutes"]
        long_break_minutes = settings["pomodoro_long_break_minutes"]

        pomodoro_text = (
            f"{work_minutes}/{short_break_minutes}/{long_break_minutes}"
        )
        print(f"2. Pomodoro         {pomodoro_text}")
        lock_state = "ON" if settings["windows_input_lock"] else "OFF"
        print(f"3. Windows lock     {lock_state}")
        print("0. Back")
        choice = input("\nSelect: ").strip()
        if choice == "1":
            edit_daily_goal(settings)
        elif choice == "2":
            edit_pomodoro(settings)
        elif choice == "3":
            toggle_input_lock(settings)
        elif choice == "0":
            return


def today_total(records):
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        safe_float(row.get("duration_minutes"))
        for row in records
        if row.get("date") == today
    )


def main_menu():
    records = load_records()
    settings = load_settings()
    studied, yesterday_same_time, difference = same_time_comparison(records)
    clear_screen()
    print_header("Study Logger")
    daily_goal = settings["daily_goal_minutes"]
    studied_text = format_minutes(studied)
    goal_text = format_minutes(daily_goal)
    yesterday_text = format_minutes(yesterday_same_time)
    difference_text = format_signed_minutes(difference)

    print(f"Today {studied_text} / {goal_text}")
    print(progress_bar(studied, daily_goal))
    print(f"Yesterday now {yesterday_text} · {difference_text}")
    print("\n1. Study")
    print("2. Manual Log")
    print("3. Records")
    print("4. Analysis")
    print("5. Settings")
    print("0. Exit")

def startup_screen():
    clear_screen()

    logo = [
        "╔══════════════════════════════════════════════════════╗",
        "║                                                      ║",
        "║              S T U D Y   L O G G E R                 ║",
        "║                                                      ║",
        "║                  Author: August0422                  ║",
        "║                                                      ║",
        "╚══════════════════════════════════════════════════════╝",
    ]

    # Print the logo with a short reveal animation.
    for line in logo:
        print(line)
        time.sleep(0.06)

    print()

    # Animated loading bar.
    width = 30
    for i in range(width + 1):
        percent = int(i / width * 100)
        bar = "█" * i + "░" * (width - i)

        print(
            f"\r            Initializing  {bar} {percent:3d}%",
            end="",
            flush=True,
        )

        time.sleep(0.025)

    print("\n")
    print("                         Ready")
    time.sleep(0.45)

    clear_screen()

def main():
    ensure_data_file()
    load_settings()
    startup_screen()
    while True:
        main_menu()
        choice = input("\nSelect: ").strip()
        if choice == "1":
            study_menu()
        elif choice == "2":
            manual_log()
        elif choice == "3":
            records_menu()
        elif choice == "4":
            analysis()
        elif choice == "5":
            settings_menu()
        elif choice == "0":
            clear_screen()
            print("Study Logger closed.")
            break


if __name__ == "__main__":
    main()
