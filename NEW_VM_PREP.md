# New VM Preparation

## Current state

- Source server: Ubuntu 22.04.3 LTS
- Source Asterisk: `GIT-21-21.0.0-pre1-2-ga75035be55`
- Target server: `ubuntu@192.168.88.172`
- Target OS currently: Ubuntu 24.04.2 LTS
- `sudo` is not available for `ubuntu`

## Recommendation

For the lowest-risk migration, rebuild the new VM on Ubuntu 22.04.x and install the same Asterisk version/build options as the current production server.

If you keep Ubuntu 24.04, you must treat this as a platform change and run a separate compatibility test for:

- Asterisk build dependencies
- ODBC modules
- PJSIP behavior
- AGI/Python dependencies
- audio/codec modules

## Required access

To prepare the VM, one of these is required:

- `root@192.168.88.172`
- passwordless `sudo` for `ubuntu`
- temporary sudo password for `ubuntu`

Without that, only user-home staging is possible, not package installation or system deployment.

## Required packages on target

Minimum runtime packages to match the current server:

```bash
apt-get update
apt-get install -y \
  build-essential git curl wget vim rsync unzip tar \
  subversion pkg-config autoconf automake libtool \
  libxml2-dev libncurses5-dev uuid-dev libjansson-dev libssl-dev \
  libsqlite3-dev libedit-dev libnewt-dev libcurl4-openssl-dev \
  libogg-dev libvorbis-dev libspeex-dev libspeexdsp-dev \
  libopus-dev libgmime-3.0-dev liblua5.2-dev \
  unixodbc unixodbc-dev odbcinst odbc-mariadb mariadb-client \
  lame python3 python3-pip python3-venv \
  sngrep tcpdump net-tools
```

If compiling from source, also install:

```bash
apt-get install -y libxslt1-dev libiksemel-dev
```

## Build approach

Because production runs a custom git build, do not replace it with Ubuntu package `asterisk` unless you first verify exact module parity.

Preferred approach:

1. Clone the exact Asterisk source revision or obtain the original source tree/package used on `asterisk-root`.
2. Copy the output of `menuselect.makeopts` from production if available.
3. Build and install the same module set.

Example skeleton:

```bash
cd /usr/local/src
git clone https://gerrit.asterisk.org/asterisk asterisk-src
cd asterisk-src
git checkout a75035be55
contrib/scripts/install_prereq install
./bootstrap.sh
./configure
make menuselect.makeopts
make -j"$(nproc)"
make install
make samples
make config
ldconfig
```

Note: `make samples` may overwrite configs. Use only before restoring production configs, or skip it if you restore `/etc/asterisk` immediately after install.

## Files to restore from source

```text
/etc/asterisk
/var/lib/asterisk
/var/spool/asterisk
/var/log/asterisk
/var/lib/asterisk/agi-bin
/etc/asterisk/scripts
/etc/odbc.ini
/etc/odbcinst.ini
```

## Ownerships after restore

```bash
chown -R asterisk:asterisk /etc/asterisk
chown -R asterisk:asterisk /var/lib/asterisk
chown -R asterisk:asterisk /var/spool/asterisk
chown -R asterisk:asterisk /var/log/asterisk
chmod -R u+rwX,g+rwX /var/lib/asterisk/agi-bin
```

## Network prerequisites

Target VM must be checked for:

- SIP `5060/udp`
- AMI `5038/tcp`
- HTTP `8088/tcp`
- RTP `10000-20000/udp`
- access to DB host
- access to SIP provider networks

## Mandatory config updates before first traffic

Review and update these values on target:

- `external_media_address`
- `external_signaling_address`
- `turnaddr`
- any `permit=` ACLs if dependent systems move
- provider IP allowlists

## Suggested preparation sequence

1. Obtain root-level access on `192.168.88.172`.
2. Decide whether to reinstall target OS to Ubuntu 22.04.
3. Install build/runtime dependencies.
4. Install matching Asterisk build.
5. Restore configs, AGI, sounds, spool layout, ODBC config.
6. Validate `asterisk -rx 'odbc show all'`.
7. Keep provider traffic on old server until dark validation passes.
