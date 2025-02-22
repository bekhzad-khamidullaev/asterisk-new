import sqlite3

# Connect to the database (or create it if it doesn't exist)
conn = sqlite3.connect('/etc/asterisk/scripts/alarm_clock.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Create the alarms table
cursor.execute('''
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    date TEXT NOT NULL,
    phone TEXT NOT NULL
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and table created successfully.")
