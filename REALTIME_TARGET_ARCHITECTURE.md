# Realtime Target Architecture

Goal for the new VM `192.168.88.172`:
- keep dialplan static
- move PJSIP objects to realtime MariaDB
- use realtime for queue members
- keep `queue_log`, CDR and application tables in MariaDB

## Recommended scope

Use realtime for:
- `ps_endpoints`
- `ps_auths`
- `ps_aors`
- `ps_endpoint_id_ips`
- `ps_domain_aliases` if needed later
- `queue_members`

Keep static:
- `extensions.conf`
- `queues.conf` at the first stage
- `rtp.conf`
- `manager.conf`
- AGI scripts
- survey and alarm business logic

Reason:
- this instance has complex queue, survey and post-call logic
- realtime dialplan would add database dependency to every routing decision
- `queue_members` is already in MariaDB and is the safest realtime target
- PJSIP realtime gives operational flexibility without rewriting the dialplan

## Current state

Current config is mostly static:
- `pjsip.conf` contains provider trunks, DIDs and templates
- `extensions.conf` contains queue and survey logic
- `extconfig.conf` currently uses realtime only for `queue_log`

Current database already has:
- `queue_members`
- `cdr`
- `queuelog`
- app tables such as `survey`, `settings_*`, `agents_new`

Current database does not yet have:
- `ps_endpoints`
- `ps_auths`
- `ps_aors`
- `ps_endpoint_id_ips`

## Safe migration order

1. Create realtime PJSIP tables in local `asterisk_db`.
2. Populate those tables only for trunk-side and DID-side objects from `pjsip.conf`.
3. Enable sorcery/extconfig mappings for PJSIP realtime.
4. Keep `pjsip.conf` only for transports and reusable templates during transition.
5. Verify `pjsip show endpoints`, `pjsip show aors`, `pjsip show identifies`.
6. Move queue members to realtime mode using the existing `queue_members` table.
7. Only after stable operation decide whether `queues` should also move to realtime.

## What not to do

Do not move these to realtime in the first cut:
- `extensions.conf`
- queue routing logic
- survey logic
- AGI workflow
- music on hold configuration

Do not combine these changes with:
- Ubuntu version change
- Asterisk major version change
- provider-side SIP topology change

## Target config changes

`/etc/asterisk/extconfig.conf`
- add mappings for `ps_endpoints`, `ps_auths`, `ps_aors`, `ps_endpoint_id_ips`
- keep existing `queue_log => odbc,asterisk,queuelog`
- add `queue_members => odbc,asterisk,queue_members`

`/etc/asterisk/sorcery.conf`
- enable realtime mappings under `[res_pjsip]`
- enable realtime mapping under `[res_pjsip_endpoint_identifier_ip]`

`/etc/asterisk/pjsip.conf`
- keep transports in file
- remove trunk and DID objects only after they exist in DB and are validated

## Operational model

After migration:
- add/remove DIDs in MariaDB
- change `from_user`, `context`, `set_var`, `match_header` in MariaDB
- change queue membership in MariaDB without editing `queues.conf`
- keep all routing code in static dialplan files

## Rollback

Rollback remains simple:
- comment realtime mappings in `extconfig.conf`
- comment sorcery realtime mappings in `sorcery.conf`
- restore static PJSIP objects in `pjsip.conf`
- reload `res_pjsip.so` and `app_queue.so`

This is the main reason to keep the dialplan static.
