#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime

import asterisk.ami


DB_PATH = os.environ.get("ALARM_DB_PATH", "/etc/asterisk/scripts/alarm_clock.db")
AMI_HOST = os.environ.get("ALARM_AMI_HOST", "localhost")
AMI_PORT = int(os.environ.get("ALARM_AMI_PORT", "5038"))
AMI_USERNAME = os.environ.get("ALARM_AMI_USERNAME", "admin")
AMI_SECRET = os.environ.get("ALARM_AMI_SECRET", "t3sl@admin")
ALARM_CHANNEL_TEMPLATE = os.environ.get("ALARM_CHANNEL_TEMPLATE", "SIP/{phone}")
ALARM_CONTEXT = os.environ.get("ALARM_CONTEXT", "default")
ALARM_EXTENSION = os.environ.get("ALARM_EXTENSION", "101")
ALARM_CALLER_ID = os.environ.get("ALARM_CALLER_ID", "Alarm")


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


def initiate_call(phone):
    client = asterisk.ami.AMIClient(address=AMI_HOST, port=AMI_PORT)
    try:
        client.login(username=AMI_USERNAME, secret=AMI_SECRET)
        action = asterisk.ami.SimpleAction(
            "Originate",
            Channel=ALARM_CHANNEL_TEMPLATE.format(phone=phone),
            Context=ALARM_CONTEXT,
            Exten=ALARM_EXTENSION,
            Priority=1,
            CallerID=ALARM_CALLER_ID,
        )
        return client.send_action(action)
    finally:
        client.logoff()


def get_due_alarms(cursor, current_stamp):
    cursor.execute(
        """
        SELECT id, phone
        FROM alarms
        WHERE date || time <= ?
        ORDER BY date, time, id
        """,
        (current_stamp,),
    )
    return cursor.fetchall()


def main():
    now = datetime.now()
    current_stamp = now.strftime("%Y%m%d%H%M")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        create_table(cursor)

        for alarm_id, phone in get_due_alarms(cursor, current_stamp):
            response = initiate_call(phone)
            if getattr(response, "is_error", lambda: False)():
                continue
            cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))

        conn.commit()


if __name__ == "__main__":
    main()
