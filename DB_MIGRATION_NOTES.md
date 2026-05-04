# DB Migration Notes

New VM `192.168.88.172` now has a local MariaDB instance for Asterisk.

Data scope:
- Full schema of `asterisk_db`
- All small/service tables migrated in full
- `cdr` migrated only for records from `2025-12-09 00:00:00`
- `queuelog` migrated only for records from `2025-12-09 00:00:00`

Row counts after import on `192.168.88.172`:
- `cdr`: 412422
- `queuelog`: 720578

ODBC on the new VM is switched to local MariaDB:
- `/etc/odbc.ini` `[MariaDB]` now points to `127.0.0.1`
- Asterisk `res_odbc` reload succeeded
- `odbc show all` shows active DSN `asterisk -> MariaDB`

Important:
- Historical records before `2025-12-09` were not imported to the new VM
- If full archive is needed later, it should be migrated separately as a background task
