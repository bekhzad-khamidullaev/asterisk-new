# Recording Retention

This keeps the latest 3 calendar months in `/var/spool/asterisk/monitor`.

Anything older is:
- archived to `/var/spool/asterisk/record_backups/YYYY-MM/archive_YYYY-MM.tar.gz`
- verified with `tar -tzf`
- hashed into `archive_YYYY-MM.tar.gz.sha256`
- removed from the source directory only after archive verification

Files:
- `archive_recordings.sh`
- `asterisk-recordings-archive.cron`

Schedule:
- daily at `01:15`

Safe check:

```bash
RETENTION_MONTHS=3 /usr/local/sbin/archive_recordings.sh --dry-run
```
