# Pre-Cutover Checklist

## Build parity

- [ ] Target OS approved: preferably Ubuntu 22.04.x
- [ ] Matching Asterisk version/build installed
- [ ] Matching module set installed
- [ ] `lame`, ODBC, MariaDB client, Python, venv dependencies installed
- [ ] `asterisk` service starts cleanly

## Config and files

- [ ] `/etc/asterisk` restored
- [ ] `/var/lib/asterisk/agi-bin` restored
- [ ] `/etc/asterisk/scripts` restored
- [ ] sounds and MOH files restored
- [ ] `/var/spool/asterisk/monitor` path exists and writable
- [ ] `/etc/odbc.ini` and `/etc/odbcinst.ini` restored if used
- [ ] ownerships fixed to `asterisk:asterisk`

## Network

- [ ] target VM can reach DB
- [ ] target VM can reach SIP provider networks
- [ ] firewall allows `5060/udp`
- [ ] firewall allows `10000-20000/udp`
- [ ] firewall allows `5038/tcp` only from trusted IPs
- [ ] firewall allows `8088/tcp` only if required
- [ ] provider side allows new IP or cutover IP move is ready

## Config review specific to this repo

- [ ] `external_media_address` updated
- [ ] `external_signaling_address` updated
- [ ] `turnaddr` reviewed
- [ ] `manager.conf` ACLs reviewed
- [ ] `http.conf` exposure reviewed
- [ ] queue definitions loaded
- [ ] AGI paths in dialplan exist on target

## Functional checks

- [ ] `asterisk -rx 'core show version'`
- [ ] `asterisk -rx 'module show like odbc'`
- [ ] `asterisk -rx 'odbc show all'`
- [ ] `asterisk -rx 'pjsip show transports'`
- [ ] `asterisk -rx 'pjsip show endpoints'`
- [ ] `asterisk -rx 'dialplan show tash-in'`
- [ ] `asterisk -rx 'dialplan show sam-in'`
- [ ] `asterisk -rx 'queue show queue_01'`
- [ ] `asterisk -rx 'queue show queue_03'`

## Call-flow tests

- [ ] inbound call to `712031220`
- [ ] inbound call to `712031222`
- [ ] internal extension to extension call
- [ ] outbound call through trunk
- [ ] queue_01 agent answer
- [ ] queue_03 agent answer
- [ ] survey prompt after queue call
- [ ] recording created and converted to MP3
- [ ] CDR row written
- [ ] `queue_log` row written

## Integration checks

- [ ] AMI client login succeeds
- [ ] AJAM/HTTP clients connect if still used
- [ ] dependent services updated to target IP if needed

## Operational readiness

- [ ] old VM remains untouched for rollback
- [ ] provider rollback method documented
- [ ] maintenance window agreed
- [ ] test numbers and responsible engineers assigned
- [ ] live monitoring ready on both old and new nodes
