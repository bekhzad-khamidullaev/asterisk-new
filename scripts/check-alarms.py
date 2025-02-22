import sqlite3
from datetime import datetime
import asterisk.ami

def initiate_call(phone):
    client = asterisk.ami.AMIClient(address='localhost', port=5038)
    client.login(username='admin', secret='t3sl@admin')
    action = asterisk.ami.SimpleAction(
        'Originate',
        Channel=f'SIP/{phone}',
        Context='default',
        Exten='101',
        Priority=1,
        CallerID='Alarm'
    )
    response = client.send_action(action)
    client.logoff()

def main():
    conn = sqlite3.connect('/etc/asterisk/scripts/alarm_clock.db')
    cursor = conn.cursor()
    now = datetime.now()
    current_time = now.strftime("%H%M")
    current_date = now.strftime("%Y%m%d")

    cursor.execute("SELECT id, phone FROM alarms WHERE time <= ? AND date <= ?", (current_time, current_date))
    alarms = cursor.fetchall()

    for alarm in alarms:
        phone = alarm[1]
        initiate_call(phone)
        cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm[0],))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
