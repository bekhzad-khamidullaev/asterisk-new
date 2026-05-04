# Cutover Plan

## Goal

Move live SIP signaling and media handling from `asterisk-root` to `192.168.88.172` with the shortest possible interruption and a clean rollback path.

## Preconditions

- Target passed all items in [PRE_CUTOVER_CHECKLIST.md](/Users/sysadmin/Documents/asterisk-new/PRE_CUTOVER_CHECKLIST.md)
- Production changes frozen during the window
- Old server remains online
- Provider routing or NAT/floating-IP switch method is confirmed

## Preferred cutover model

Use one of these, in order of preference:

1. Move the service IP/NAT from old VM to new VM
2. Change provider routing/ACL to new VM IP
3. Repoint DNS only if endpoints truly use DNS and TTL has been lowered in advance

For a high-volume call center, DNS-only cutover is the weakest option.

## Detailed sequence

### T-60 minutes

- Confirm no config changes on old server
- Take snapshots/backups of old and new VM
- Verify target health:

```bash
asterisk -rx 'core show uptime'
asterisk -rx 'pjsip show transports'
asterisk -rx 'odbc show all'
asterisk -rx 'queue show'
```

- Verify old server health and current active calls:

```bash
asterisk -rx 'core show channels count'
asterisk -rx 'queue show'
```

### T-15 minutes

- Sync the latest configs and scripts from old to new
- Sync any new prompts or changed AGI files
- Re-run:

```bash
asterisk -rx 'core reload'
asterisk -rx 'dialplan reload'
asterisk -rx 'pjsip reload'
```

- Place final pre-cutover test calls to the new VM without provider switch if possible

### T-5 minutes

- Announce change freeze
- Watch active calls on old node:

```bash
watch -n 2 "asterisk -rx 'core show channels count'"
```

- If feasible, wait for active calls to reduce

### Cutover point

Perform exactly one switch action:

- move IP/NAT to `192.168.88.172`, or
- repoint provider SIP routing to `192.168.88.172`

Immediately after switching:

```bash
ssh ubuntu@192.168.88.172 "sudo asterisk -rx 'pjsip show transports'"
ssh ubuntu@192.168.88.172 "sudo asterisk -rx 'core show channels count'"
ssh ubuntu@192.168.88.172 "sudo asterisk -rx 'queue show'"
```

### First 5 minutes after cutover

Run controlled tests:

- inbound to Tashkent DID
- inbound to Samarkand DID
- agent receives queue call
- two-way audio confirmed
- recording file appears
- survey prompt works
- AMI consumer reconnects

### First 30 minutes after cutover

Continuously check:

```bash
asterisk -rx 'core show channels count'
asterisk -rx 'pjsip show contacts'
asterisk -rx 'queue show'
tail -f /var/log/asterisk/full
```

Database checks:

- new CDR rows arriving
- new `queue_log` rows arriving
- no AGI tracebacks

## Rollback plan

Rollback immediately if any of these happen:

- inbound calls fail
- one-way/no audio
- major agent registration loss
- queue calls stop reaching agents
- AMI-dependent CRM stops functioning
- DB logging fails

Rollback steps:

1. Revert provider routing or service IP/NAT to old server
2. Confirm `asterisk-root` receives new calls again
3. Keep new server up for inspection, but out of traffic
4. Collect logs and compare failed flows before a second attempt

## What not to do

- Do not cut over before ODBC is verified on target
- Do not delete or modify old server during the first cutover
- Do not rely on config parity only; media and DB must be tested
- Do not expose `5038` and `8088` broadly on the new VM without review

## Post-cutover stabilization

- keep old VM intact for at least 24 hours
- compare call volume and queue stats old vs new
- verify recordings for the first production hour
- rotate exposed secrets after stabilization
