# Infrastructure Blockers Before Cutover

## Current target status

- New VM `192.168.88.172` is running Asterisk `GIT-21-a75035b`
- `ODBC` to `192.168.88.197` works
- `PJSIP` transports are loaded
- Dialplan and queues are loaded
- AMI and HTTP are listening on `5038/tcp` and `8088/tcp`

## Hard blockers

### 1. Trunk networks are not reachable from the new VM

The old server has these relevant addresses:

- `192.168.88.171/24` on `ens160`
- `172.27.7.54/30` on `ens224`
- `172.27.61.131/24` on `ens256`

The old server also has a specific route:

- `172.28.7.54 via 172.27.7.53 dev ens224`

The new VM currently has only:

- `192.168.88.172/24` on `ens18`

Observed from the new VM:

- route lookup to `172.27.61.5` goes via `192.168.88.254`
- route lookup to `172.28.7.54` goes via `192.168.88.254`
- ICMP to `172.27.61.5` fails
- ICMP to `172.28.7.54` fails
- ICMP to DB host `192.168.88.197` succeeds

### 2. TURN service is present on the old server and absent on the new one

Old server:

- `turnserver` active
- listening on `192.168.88.171:3478`

New server:

- no active `coturn` or `turnserver`

This matters because `rtp.conf` currently points to:

- `turnaddr=192.168.88.171:3478`

## What infra must provide

## Option A. Match the old network topology on the new VM

Preferred for lowest risk.

Add equivalent connectivity for:

- `172.27.61.0/24` with ability to reach `172.27.61.5`
- `172.27.7.52/30` with local address replacing old `172.27.7.54`
- static route to `172.28.7.54/32` via `172.27.7.53`

If the old IPs can be moved during cutover, the safest model is:

- stop traffic to old VM
- assign the old service IPs to the new VM
- verify provider connectivity
- then cut over Asterisk

## Option B. Keep only `192.168.88.172`, but change upstream routing/ACL

Only viable if the provider/network team confirms:

- SIP traffic from `192.168.88.172` is accepted instead of old trunk-side source IPs
- return routing to `192.168.88.172` is configured
- any ACLs/firewall rules on provider side are updated

This is riskier because the current config references private trunk-side peers directly.

## Option C. Migrate TURN separately or disable it if unused

Choose one:

- install and configure `coturn` on `192.168.88.172` and update `rtp.conf`
- keep TURN on another reachable host and update `turnaddr`
- remove TURN usage only if confirmed unnecessary for active endpoints

## Concrete asks for infra/network team

1. Confirm whether the new VM can receive additional NICs or IPs in:
   - `172.27.61.0/24`
   - `172.27.7.52/30`

2. If yes, provide:
   - target IP for provider-side segment
   - target IP for `/30` segment
   - gateway details for `172.28.7.54`

3. If no, confirm provider-side acceptance of source IP `192.168.88.172`.

4. Decide what to do with TURN on `3478`.

## Recommended next move

Do not schedule live cutover until one of the above network options is explicitly implemented and validated with test traffic.
