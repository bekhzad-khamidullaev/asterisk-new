#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime

import asterisk.agi


DB_PATH = os.environ.get("ALARM_DB_PATH", "/etc/asterisk/scripts/alarm_clock.db")


def read_digits(agi, prompt, min_digits, max_digits):
    agi.stream_file(prompt)
    digits = ""

    while len(digits) < max_digits:
        timeout = -1 if not digits else 3000
        result = agi.wait_for_digit(timeout)
        if result <= 0:
            break

        digit = chr(result)
        if digit.isdigit():
            digits += digit

    if len(digits) < min_digits:
        return None

    return digits


def normalize_time(raw_value):
    if raw_value is None or len(raw_value) != 4:
        return None

    try:
        parsed = datetime.strptime(raw_value, "%H%M")
    except ValueError:
        return None

    return parsed.strftime("%H%M")


def normalize_date(raw_value):
    if raw_value is None:
        return None

    formats = {
        6: "%d%m%y",
        8: "%d%m%Y",
    }

    fmt = formats.get(len(raw_value))
    if fmt is None:
        return None

    try:
        parsed = datetime.strptime(raw_value, fmt)
    except ValueError:
        return None

    return parsed.strftime("%Y%m%d")


def normalize_phone(raw_value):
    if raw_value is None:
        return None

    digits = "".join(ch for ch in raw_value if ch.isdigit())
    if len(digits) < 3 or len(digits) > 15:
        return None

    return digits


def create_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            date TEXT NOT NULL,
            phone TEXT NOT NULL
        )
        """
    )


def main():
    agi = asterisk.agi.AGI()
    agi.answer()

    raw_time = read_digits(agi, "please-enter-the-time", 4, 4)
    raw_date = read_digits(agi, "please-enter-the-date", 6, 8)
    raw_phone = read_digits(agi, "please-enter-your-phone-number", 3, 15)

    alarm_time = normalize_time(raw_time)
    alarm_date = normalize_date(raw_date)
    phone = normalize_phone(raw_phone)

    if not all([alarm_time, alarm_date, phone]):
        agi.stream_file("invalid")
        agi.hangup()
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        create_table(cursor)
        cursor.execute(
            "INSERT INTO alarms (time, date, phone) VALUES (?, ?, ?)",
            (alarm_time, alarm_date, phone),
        )
        conn.commit()

    agi.stream_file("alarm-set")
    agi.hangup()


if __name__ == "__main__":
    main()
