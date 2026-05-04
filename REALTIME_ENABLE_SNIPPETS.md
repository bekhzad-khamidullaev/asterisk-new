# Realtime Enable Snippets

Apply these changes only after `ps_*` tables are created and populated.

## extconfig.conf

Uncomment or add:

```ini
ps_endpoints => odbc,asterisk,ps_endpoints
ps_auths => odbc,asterisk,ps_auths
ps_aors => odbc,asterisk,ps_aors
ps_domain_aliases => odbc,asterisk,ps_domain_aliases
ps_endpoint_id_ips => odbc,asterisk,ps_endpoint_id_ips
queue_members => odbc,asterisk,queue_members
queue_log => odbc,asterisk,queuelog
```

## sorcery.conf

Uncomment or add:

```ini
[res_pjsip]
endpoint=realtime,ps_endpoints
auth=realtime,ps_auths
aor=realtime,ps_aors
domain_alias=realtime,ps_domain_aliases

[res_pjsip_endpoint_identifier_ip]
identify=realtime,ps_endpoint_id_ips
```

## Validation commands

Run on the new VM:

```bash
sudo -u asterisk asterisk -rx 'module reload res_odbc.so'
sudo -u asterisk asterisk -rx 'module reload res_pjsip.so'
sudo -u asterisk asterisk -rx 'realtime mysql status'
sudo -u asterisk asterisk -rx 'pjsip show endpoints'
sudo -u asterisk asterisk -rx 'pjsip show aors'
sudo -u asterisk asterisk -rx 'pjsip show identifies'
sudo -u asterisk asterisk -rx 'queue show'
```

## Recommended rollout

1. Put only one non-critical DID into realtime.
2. Reload `res_pjsip.so`.
3. Confirm inbound call, recording, queue routing and survey.
4. Move the remaining DIDs.
5. Move queue membership control to the `queue_members` table.

Do not move all trunks at once.
