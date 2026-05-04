# Zabbix -> Asterisk Voice Alert (edge-tts + AMI)

## Goal
Implement native Zabbix voice notifications where `tshttzbx` triggers calls through Asterisk AMI on `tshttaster`, and Asterisk plays message text synthesized by `edge-tts`.

## Architecture
1. Zabbix Action (event source: Triggers) executes media script `zbxAsteriskCall.py`.
2. Script connects to Asterisk AMI and runs `Originate` for responsible users.
3. Asterisk context `zabbix-alert-call` runs AGI `zabbix_tts_alert.py`.
4. AGI generates/caches WAV via `edge-tts` + `sox` and returns playback path.
5. Dialplan plays generated file to callee.

## Files in this repo
- Zabbix media script: `scripts/zbxAsteriskCall.py`
- Asterisk AGI TTS: `scripts/zabbix_tts_alert.py`
- Dialplan context: `zabbix-alert-call.context`
- Deploy helper: `scripts/deploy_zabbix_voice_alert_stack.sh`
- Asterisk setup helper: `scripts/setup_asterisk_voice_alert.sh`
- Zabbix setup helper: `scripts/setup_zabbix_voice_alert.sh`
- Zabbix API auto-config: `scripts/configure_zabbix_voice_alert.py`
- One-shot server deploy: `scripts/deploy_voice_alert_to_servers.sh`

## One-shot deployment (both servers)
From this repo, run:
```bash
export AMI_SECRET='YOUR_STRONG_SECRET'
export ZBX_IP_FOR_AMI='IP_OF_TSHTTZBX'
bash scripts/deploy_voice_alert_to_servers.sh
```

Then configure Zabbix Media type + Action via API:
```bash
python3 scripts/configure_zabbix_voice_alert.py \
  --api-url 'https://<zabbix-host>/api_jsonrpc.php' \
  --username '<zabbix-admin>' \
  --password '<zabbix-password>' \
  --usergroup-id '<responsible_user_group_id>' \
  --ami-host '10.10.134.62' \
  --ami-secret 'YOUR_STRONG_SECRET'
```

Optional: add `--with-recovery` to call on recovery events too.

## Deploy

### On tshttaster (Asterisk)
1. Install dependencies:
   - `python3 -m pip install edge-tts`
   - `sox` package (`apt install sox` or equivalent)
2. Configure AMI user in `/etc/asterisk/manager.conf`:
```ini
[zabbix_call]
secret = <STRONG_SECRET>
read = none
write = originate
permit = <IP_tshttzbx>/255.255.255.255
deny = 0.0.0.0/0.0.0.0
```
3. Reload manager: `asterisk -rx "manager reload"`

### On target host where files are deployed
Run:
```bash
sudo bash scripts/deploy_zabbix_voice_alert_stack.sh \
  --zbx-alertscripts /usr/lib/zabbix/alertscripts \
  --agi-bin /var/lib/asterisk/agi-bin \
  --extensions /etc/asterisk/extensions.conf
```

## Zabbix UI setup
Create Media type:
- Type: `Script`
- Name: `Asterisk Voice Call`
- Script name: `zbxAsteriskCall.py`

Script parameters (in exact order):
1. `{ALERT.SENDTO}`
2. `{ALERT.SUBJECT}`
3. `{ALERT.MESSAGE}`
4. `{EVENT.VALUE}`
5. `10.10.134.62`                    # AMI host (tshttaster)
6. `5038`                            # AMI port
7. `zabbix_call`                     # AMI username
8. `<AMI_SECRET>`                    # AMI secret
9. `PJSIP/{number}@712031212`        # Channel template
10. `zabbix-alert-call`              # Dialplan context
11. `s`                              # Extension
12. `1`                              # Priority
13. `Zabbix Alert`                   # CallerID
14. `45000`                          # Timeout (ms)
15. `1`                              # only_problem (1=yes, 0=problem+recovery)
16. `ru`                             # voice: ru|uz
17. `145`                            # speed (120..190 recommended)
18. `420`                            # max_chars
19. `{EVENT.ID}`                     # event_id for dedupe
20. `900`                            # dedupe ttl seconds
21. `summary`                        # text_mode: fast|subject|summary
22. `2`                              # repeat count (1..3)

User media:
- Type: `Asterisk Voice Call`
- Send to: phone number, e.g. `998901234567`

## Mapping responsibilities by host groups
Best-practice pattern in Zabbix:
1. Create User groups by responsibility zone.
2. Put responsible users in these groups and add media `Asterisk Voice Call`.
3. Build Actions with conditions by Host group / tags / severity.
4. Use escalation steps and stop escalation when event is acknowledged.

## Runtime behavior
- Default mode calls only on `PROBLEM` (`only_problem=1`).
- If `only_problem=0`, script also calls on `RECOVERY`.
- The script deduplicates calls per `event_id + phone + event_value` for `dedupe_ttl_sec`.
- Multiple phones are supported in `Send to` (`comma/semicolon/space` separated).

## Validation checklist
1. From Zabbix media type, run Test to a real number.
2. Check Zabbix server output for `OK: calls=...`.
3. On Asterisk server:
   - `asterisk -rx "manager show connected"`
   - `asterisk -rx "core show channels"`
   - `tail -f /var/log/asterisk/full`
4. Check generated cache files under `/var/lib/asterisk/sounds/zabbix-alert/cache`.

## Failure handling
- If TTS generation fails, dialplan falls back to `Playback(beeperr)`.
- Keep AMI access restricted by source IP and least privileges.
- Because `edge-tts` uses external service, keep short alert text and rely on cache.
