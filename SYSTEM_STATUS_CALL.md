# System Status Call

This feature makes the new VM call a configured number every day at a configured time and speak a Russian status report about the server and Asterisk.

Files:
- `system_status_call.py`
- `system_status_call.ini`
- dialplan context `system-status-call` in `extensions.conf`

What the report includes:
- Asterisk CLI availability
- local MariaDB availability
- ODBC availability
- TURN port `3478`
- free RAM
- free disk space
- system load average

How scheduling works:
- the script runs every minute from cron
- it places the call only when the current local time matches `time = HH:MM`
- it stores the last successful call date in `.last_report_date`
- this prevents duplicate calls on the same day

Config:
- `enabled = yes|no`
- `time = 06:00`
- `number = ...`
- `channel_template = PJSIP/{number}@712031212`

Activation:
1. Put the target number into `system_status_call.ini`
2. Set `enabled = yes`
3. Reload dialplan
4. Test once with `--run-now`

Important:
- by default the feature is deployed disabled
- this avoids accidental outbound calls before the final number and route are confirmed
