# Asterisk Migration Runbook

## Scope

This repository contains a production Asterisk configuration with:

- PJSIP trunking and inbound routing
- Call queues
- Call recording with `MixMonitor`
- AGI/Python integrations
- ODBC/MariaDB integration
- AMI/AJAM/HTTP interfaces

The migration target must be treated as a full application move, not only a config copy.

## Repo-specific findings

- SIP/PJSIP transport and provider routing are defined in [pjsip.conf](/Users/sysadmin/Documents/asterisk-new/pjsip.conf#L3) and [pjsip.conf](/Users/sysadmin/Documents/asterisk-new/pjsip.conf#L67).
- External/public addressing is hardcoded in [pjsip.conf](/Users/sysadmin/Documents/asterisk-new/pjsip.conf#L9) and must be updated on the new VM.
- Inbound routing, queues, surveys, AGI, and recording logic are in [extensions.conf](/Users/sysadmin/Documents/asterisk-new/extensions.conf#L1), [extensions.conf](/Users/sysadmin/Documents/asterisk-new/extensions.conf#L120), and [extensions.conf](/Users/sysadmin/Documents/asterisk-new/extensions.conf#L313).
- Queue behavior is defined in [queues.conf](/Users/sysadmin/Documents/asterisk-new/queues.conf#L1).
- ODBC uses MariaDB credentials from [res_odbc.conf](/Users/sysadmin/Documents/asterisk-new/res_odbc.conf#L1).
- `queue_log` is configured through ODBC in [extconfig.conf](/Users/sysadmin/Documents/asterisk-new/extconfig.conf#L112).
- AMI is enabled on all interfaces in [manager.conf](/Users/sysadmin/Documents/asterisk-new/manager.conf#L1).
- HTTP is enabled on port 8088 in [http.conf](/Users/sysadmin/Documents/asterisk-new/http.conf#L1).
- RTP uses ports `10000-20000`, ICE, STUN, and TURN in [rtp.conf](/Users/sysadmin/Documents/asterisk-new/rtp.conf#L4).
- Recordings are written under `/var/spool/asterisk/monitor/...` and transcoded with `lame` in [extensions.conf](/Users/sysadmin/Documents/asterisk-new/extensions.conf#L314).

## What must be migrated

## 1. OS and packages

- Same Linux family and major version if possible
- Same Asterisk major/minor version
- Same `pjproject` compatibility
- `lame`, ODBC packages, MariaDB client libs, Python runtime, Python venv dependencies
- `systemd` unit overrides, cron jobs, logrotate, fail2ban, firewall rules

## 2. Asterisk runtime data

- `/etc/asterisk`
- `/var/lib/asterisk`
- `/var/spool/asterisk`
- `/var/log/asterisk`
- `/usr/lib/asterisk/modules` if custom modules are used
- `/var/lib/asterisk/agi-bin`
- `/etc/odbc.ini`, `/etc/odbcinst.ini` if used outside repo

## 3. External dependencies

- MariaDB database and grants for user `asterisk`
- SIP provider ACL/allowed source IP update
- Any CRM or softphone integrations using AMI/AJAM/HTTP
- TURN server reachability if still required
- Monitoring and alerting

## 4. Secrets and certificates

- SIP auth secrets if stored outside this repo
- AMI secrets
- TLS certs and keys
- SSH keys used for recording sync or automation

## Migration strategy

Recommended strategy: build the new VM in parallel, restore data, run it in dark mode, then switch signaling to the new IP during a low-traffic maintenance window.

Avoid in-place replacement unless you already have tested VM snapshots and rollback automation.

## Phase 1. Discovery on the current server

Capture the real state from `asterisk-root` before doing anything:

```bash
asterisk -rx 'core show version'
asterisk -rx 'module show like odbc'
asterisk -rx 'pjsip show transports'
asterisk -rx 'pjsip show endpoints'
asterisk -rx 'queue show'
asterisk -rx 'dialplan show'
systemctl cat asterisk
crontab -l
ss -lntup | egrep '5060|5061|8088|8089|5038|10000'
```

Also collect:

- exact OS version
- package list
- active firewall/NAT rules
- database host and schema names
- location of all custom scripts outside `/etc/asterisk`

## Phase 2. Prepare the new VM

- Match CPU/RAM sizing to current peak load, with headroom
- Reserve the final private and public IPs before cutover
- Open at minimum:
  - SIP signaling: `5060/udp` and any TLS/WSS ports in use
  - RTP: `10000-20000/udp`
  - AMI: `5038/tcp` only from trusted IPs
  - HTTP: `8088/tcp` only if required
- Set hostname, NTP, timezone, limits, and kernel networking defaults

If the new VM gets a different public IP, update at least:

- `external_media_address`
- `external_signaling_address`
- provider-side ACL or allowed source IP
- firewall/NAT rules

## Phase 3. Install identical runtime

- Install the same Asterisk version
- Install ODBC and MariaDB drivers
- Install `lame`
- Recreate Python venvs and AGI dependencies
- Restore the same module set

Do not start taking production traffic yet.

## Phase 4. Restore configuration and data

Restore:

- `/etc/asterisk/*`
- AGI scripts under `/var/lib/asterisk/agi-bin` and `/etc/asterisk/scripts` if both are used
- sound files under `/var/lib/asterisk/sounds`
- music-on-hold assets
- recent recordings if they must remain available locally after cutover

Validate ownerships:

```bash
chown -R asterisk:asterisk /etc/asterisk /var/lib/asterisk /var/spool/asterisk /var/log/asterisk
find /var/lib/asterisk/agi-bin -type f -name '*.py' -exec chmod 755 {} \;
```

## Phase 5. Database and integrations

Confirm ODBC from the new VM:

```bash
isql -v MariaDB
asterisk -rx 'odbc show all'
```

Verify:

- CDR writes
- `queue_log` writes
- survey/AGI writes
- CRM or websocket consumers of AMI/AJAM/HTTP

If the DB remains remote, test latency and connection pool behavior under load.

## Phase 6. Pre-production validation

Before any switch:

- `asterisk -rx 'core reload'`
- `asterisk -rx 'pjsip reload'`
- `asterisk -rx 'dialplan reload'`
- `asterisk -rx 'dialplan show tash-in'`
- `asterisk -rx 'dialplan show sam-in'`
- `asterisk -rx 'queue show queue_01'`
- test inbound calls per DID/city
- test outbound internal and trunk calls
- test queue answer flow
- test survey flow
- test recording creation and MP3 conversion
- test AMI login from dependent systems

Mandatory validation points from this repo:

- inbound DIDs mapped in `pjsip.conf`
- queues `queue_01`, `queue_02`, `queue_03`, `queue_05`, `queue_07`
- `MixMonitor` output under `/var/spool/asterisk/monitor`
- AGI scripts `alarm.py` and `survey.py`

## Phase 7. Cutover

Preferred order:

1. Freeze config changes on the old server.
2. Sync latest configs, scripts, prompts, and any required recordings.
3. Stop new agent/device registrations to the old node if applicable.
4. Update provider routing or floating IP/NAT to point to the new VM.
5. Reload or restart Asterisk on the new VM only after all dependencies are confirmed healthy.
6. Place controlled test calls immediately.
7. Monitor live queue depth, agent registrations, RTP, and DB writes for at least 30-60 minutes.

If endpoints register directly to Asterisk, plan for device re-registration behavior and DNS/TTL effects.

## Rollback

Rollback must be prepared before cutover:

- old VM stays powered on and unchanged
- old provider/IP routing values are documented
- restore command list is ready
- DB writes from the new VM can be stopped cleanly

Rollback trigger examples:

- one-way audio
- mass registration failures
- queue events missing from DB
- AGI failures on surveys
- AMI clients disconnected

## High-risk items in this repo

- Public IP is hardcoded in PJSIP WSS transport.
- RTP/NAT behavior is environment-sensitive.
- AMI and HTTP listeners are exposed broadly and may break or overexpose services after IP changes.
- Recording path and `lame` conversion must exist and be writable.
- Queue flow depends on custom channel variables and post-call survey logic.
- ODBC is not optional because `queue_log` is configured there.

## Recommended maintenance window approach

- Build and validate the new VM during business hours without traffic.
- Execute cutover in the lowest call-volume window.
- Keep the old VM as hot rollback for at least 24 hours.
- Do not delete old recordings or old VM snapshots until billing/reporting checks pass.

## Minimal checklist for go-live

- New VM answers inbound test calls
- Agents can receive queue calls
- Two-way audio works
- Recordings are created and converted to MP3
- CDR and `queue_log` rows appear in DB
- AMI clients reconnect successfully
- No critical errors in `/var/log/asterisk/full`

## Next actions

1. Inventory the current production host `asterisk-root` with the discovery commands above.
2. Confirm the target VM IP model: same IP, NAT switch, or new public IP.
3. Build the new VM with the same Asterisk version and dependencies.
4. Run a dark launch with provider traffic still pointed at the old node.
5. Schedule a short cutover window with rollback ready.
