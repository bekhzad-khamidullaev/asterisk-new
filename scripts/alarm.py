#!/usr/bin/env python3
import asterisk.agi
import sqlite3
from datetime import datetime

def get_input(agi, prompt, max_digits):
    agi.stream_file(prompt)
    result = agi.wait_for_digit(-1)
    input_digits = ''
    while result.isdigit():
        input_digits += chr(result)
        if len(input_digits) >= max_digits:
            break
        result = agi.wait_for_digit(3000)
    return input_digits

def main():
    agi = asterisk.agi.AGI()
    agi.answer()

    # Get the time for the alarm
    time = get_input(agi, 'please-enter-the-time', 4)
    date = get_input(agi, 'please-enter-the-date', 6)
    phone = get_input(agi, 'please-enter-your-phone-number', 10)

    # Connect to the database
    conn = sqlite3.connect('/etc/asterisk/scripts/alarm_clock.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS alarms (id INTEGER PRIMARY KEY, time TEXT, date TEXT, phone TEXT)")
    cursor.execute("INSERT INTO alarms (time, date, phone) VALUES (?, ?, ?)", (time, date, phone))
    conn.commit()
    conn.close()

    agi.stream_file('alarm-set')
    agi.hangup()

if __name__ == '__main__':
    main()
