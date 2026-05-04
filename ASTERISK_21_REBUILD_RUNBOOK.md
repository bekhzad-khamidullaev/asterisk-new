# Asterisk 21 Rebuild Runbook for `192.168.88.171`

Target:
- Server: `ubuntu@192.168.88.171`
- Current version: `Asterisk GIT-21-43bf36e`
- Target version: `Asterisk GIT-21-21.0.0-pre1-2-ga75035be55`

Goal:
- Build the target Asterisk version on the new server without impacting live traffic during preparation.
- Keep the production cutover to the shortest possible outage.
- Preserve a fast rollback path.

## Expected Downtime

If preparation is completed in advance and the build is validated before cutover:
- Realistic outage: `30-90 seconds`
- Safe maintenance window to reserve: `15 minutes`

If build options, module loading, or ABI compatibility differ unexpectedly:
- Possible outage during rollback/restart: `5-15 minutes`

There is no true zero-downtime path if the running `asterisk` process must be replaced in place.

## Important Assumptions

- Do not rebuild over the live process during business hours.
- Do not stop `asterisk` while compiling.
- Only the final binary switch requires downtime.
- Use `core reload` for config reloads in normal operations, but a binary replacement requires a full service restart.

## Current State Verified on `192.168.88.171`

- Ubuntu `24.04.2 LTS`
- Build toolchain already present:
  - `build-essential`
  - `gcc`, `g++`, `make`
  - `libxml2-dev`
  - `libsqlite3-dev`
  - `uuid-dev`
  - `libjansson-dev`
  - `libssl-dev`
  - `libedit-dev`
  - `libsrtp2-dev`
  - `libcurl4-openssl-dev`
  - `libspeexdsp-dev`
  - `unixodbc-dev`

Missing packages may still be needed depending on the exact old build flags:
- `libncurses5-dev` or `libncurses-dev`
- `libmariadb-dev`
- `libldap2-dev`
- `libiksemel-dev`
- `subversion`

## Phase 1: Safe Preparation, No Service Impact

Run everything in a separate source tree:

```bash
ssh ubuntu@192.168.88.171
sudo mkdir -p /usr/local/src/asterisk-rebuild
sudo chown -R ubuntu:ubuntu /usr/local/src/asterisk-rebuild
cd /usr/local/src/asterisk-rebuild
```

Install any missing build dependencies:

```bash
sudo apt update
sudo apt install -y \
  build-essential gcc g++ make git subversion pkg-config autoconf automake libtool \
  libxml2-dev libsqlite3-dev uuid-dev libjansson-dev libssl-dev libedit-dev \
  libsrtp2-dev libcurl4-openssl-dev libspeexdsp-dev unixodbc-dev \
  libncurses-dev libmariadb-dev libldap2-dev
```

Fetch the exact Asterisk source. Preferred approach is the exact git commit/tag if available:

```bash
cd /usr/local/src/asterisk-rebuild
git clone https://gerrit.asterisk.org/asterisk asterisk-21-old
cd asterisk-21-old
git fetch --all --tags
git checkout a75035be55
```

If `a75035be55` is unavailable in the remote you use, fetch the archived source tarball or copy the old source tree from a backup. Do not guess at a nearby revision if bit-for-bit parity matters.

Capture current live build metadata from the running server before compiling:

```bash
echo admin | sudo -S asterisk -rx 'core show settings' > /tmp/ast-core-settings.txt
echo admin | sudo -S asterisk -rx 'module show' > /tmp/ast-module-show.txt
echo admin | sudo -S asterisk -rx 'pjsip show endpoints' > /tmp/ast-pjsip-endpoints.txt
echo admin | sudo -S asterisk -rx 'odbc show all' > /tmp/ast-odbc-show.txt
dpkg -l > /tmp/dpkg-list-before-asterisk-rebuild.txt
```

## Phase 2: Match Build Options Before Install

Prepare the source:

```bash
cd /usr/local/src/asterisk-rebuild/asterisk-21-old
./bootstrap.sh
./configure
make menuselect.makeopts
```

Before enabling or disabling anything, snapshot `menuselect.makeopts`:

```bash
cp menuselect.makeopts menuselect.makeopts.initial
```

Minimum modules to verify are enabled:
- `res_pjsip`
- `chan_pjsip`
- `res_pjsip_transport_websocket`
- `res_http_websocket`
- `res_srtp`
- `res_rtp_asterisk`
- `res_odbc`
- `func_odbc`
- `cdr_adaptive_odbc`
- `app_queue`
- `codec_opus` if it existed in the old build and licensing allows it

Open menuselect:

```bash
make menuselect
```

Then compile without installing yet:

```bash
make -j"$(nproc)"
```

Validate the built binary and module dependencies:

```bash
./asterisk -V
find ./addons ./main ./res ./channels ./apps -name '*.so' | head
ldd ./asterisk | grep 'not found' || true
find ./ -name 'res_srtp.so' -o -name 'res_http_websocket.so' -o -name 'chan_pjsip.so'
```

## Phase 3: Stage the Install, Still No Cutover

Do not stop the running service yet.

Install into the system paths only after the build is known-good:

```bash
cd /usr/local/src/asterisk-rebuild/asterisk-21-old
sudo make install
sudo make samples
sudo make config
sudo ldconfig
```

Immediately snapshot the newly installed binaries and modules so rollback is mechanical:

```bash
sudo mkdir -p /opt/asterisk-binary-snapshots/after-target-install
sudo rsync -a /usr/sbin/asterisk /opt/asterisk-binary-snapshots/after-target-install/
sudo rsync -a /usr/lib/asterisk/ /opt/asterisk-binary-snapshots/after-target-install/usr-lib-asterisk/
```

Also snapshot the current live binaries before cutover:

```bash
sudo mkdir -p /opt/asterisk-binary-snapshots/before-cutover
sudo rsync -a /usr/sbin/asterisk /opt/asterisk-binary-snapshots/before-cutover/
sudo rsync -a /usr/lib/asterisk/ /opt/asterisk-binary-snapshots/before-cutover/usr-lib-asterisk/
```

## Phase 4: Pre-Cutover Checklist

All of the following must be green before restart:

- `echo admin | sudo -S asterisk -rx 'module show like res_srtp'`
- `echo admin | sudo -S asterisk -rx 'module show like res_http_websocket'`
- `echo admin | sudo -S asterisk -rx 'module show like chan_pjsip'`
- `echo admin | sudo -S asterisk -rx 'odbc show all'`
- `ss -ltnup | egrep '5060|8088|8089'`
- `ss -lunp | egrep '3478|10000|20000'`
- `docker ps` for `queue_stats` and any TURN-related containers if applicable
- `/etc/asterisk`, `/var/lib/asterisk`, `/var/spool/asterisk`, `/var/www/html`, `/opt/queue_stats` all backed up
- `systemctl cat asterisk` reviewed
- `asterisk.conf`, `modules.conf`, `pjsip.conf`, `rtp.conf`, `res_odbc.conf`, `func_odbc.conf`, `manager.conf` backed up

Recommended backup commands:

```bash
sudo tar -C / -czf /root/asterisk-pre-cutover-configs.tgz \
  etc/asterisk \
  var/lib/asterisk \
  var/spool/asterisk \
  var/www/html \
  opt/queue_stats
```

## Phase 5: Cutover Procedure

This is the outage window.

1. Announce maintenance start.
2. Stop new changes in UI/admin tooling.
3. Restart Asterisk onto the rebuilt binary.

Commands:

```bash
ssh ubuntu@192.168.88.171
echo admin | sudo -S systemctl stop asterisk
echo admin | sudo -S systemctl start asterisk
echo admin | sudo -S systemctl is-active asterisk
echo admin | sudo -S asterisk -V
```

Immediate smoke checks:

```bash
echo admin | sudo -S asterisk -rx 'module show like res_srtp'
echo admin | sudo -S asterisk -rx 'module show like res_http_websocket'
echo admin | sudo -S asterisk -rx 'pjsip show transports'
echo admin | sudo -S asterisk -rx 'pjsip show endpoints'
echo admin | sudo -S asterisk -rx 'odbc show all'
echo admin | sudo -S asterisk -rx 'manager show connected'
```

Operational smoke tests:

- WebRTC operator registers successfully
- One inbound call reaches queue
- One outbound call connects
- Operator hears caller
- Caller hears operator
- Recording created
- TURN relay candidates still appear in browser

## Phase 6: Rollback Procedure

Rollback trigger examples:
- `asterisk -V` not showing expected version
- required modules missing
- PJSIP endpoints not loading
- ODBC failures
- WebRTC registration broken
- one-way/no-audio persists or worsens

Rollback commands:

```bash
ssh ubuntu@192.168.88.171
echo admin | sudo -S systemctl stop asterisk
echo admin | sudo -S rsync -a /opt/asterisk-binary-snapshots/before-cutover/asterisk /usr/sbin/asterisk
echo admin | sudo -S rsync -a --delete /opt/asterisk-binary-snapshots/before-cutover/usr-lib-asterisk/ /usr/lib/asterisk/
echo admin | sudo -S ldconfig
echo admin | sudo -S systemctl start asterisk
echo admin | sudo -S asterisk -V
```

Then re-run the same smoke tests.

## Operational Recommendation

Best practice for this call center:
- complete build and validation during daytime without touching the service
- perform the binary restart only in low traffic hours
- reserve a `15 minute` maintenance window
- communicate expected hard outage as `up to 2 minutes`, with rollback window up to `15 minutes`

## What Is Still Missing

The old server `192.168.88.172` was unreachable during this preparation, so the following should still be captured from any available backup before final cutover if possible:
- exact old git commit checkout source tree
- old `menuselect.makeopts`
- old `buildopts.h`
- `module show` from the old binary

Without those, the rebuild can still be done, but parity is “best effort” rather than guaranteed bit-for-bit.
