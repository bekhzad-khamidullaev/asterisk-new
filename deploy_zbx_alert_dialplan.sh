#!/usr/bin/env bash
set -euo pipefail

cfg="/etc/asterisk/extensions.conf"
tmp="$(mktemp)"

python3 - "$cfg" "$tmp" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
target = Path(sys.argv[2])

old = """[zabbix-alert-call]
exten => s,1,NoOp(Zabbix voice alert call)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(CHANNEL(language)=ru)
 same => n,AGI(zabbix_tts_alert.py)
 same => n,Wait(1)
 same => n,Hangup()
"""

new = """[zabbix-alert-call]
exten => s,1,NoOp(Zabbix voice alert call)
 same => n,Set(CHANNEL(language)=ru)
 same => n,Set(ALERT_PREGENERATE=1)
 same => n,AGI(zabbix_tts_alert.py)
 same => n,Answer()
 same => n,Wait(1)
 same => n,ExecIf($["${ALERT_PLAYBACK}" != ""]?Playback(${ALERT_PLAYBACK}))
 same => n,ExecIf($["${ALERT_PLAYBACK}" = ""]?Playback(beeperr))
 same => n,Hangup()
"""

if old in src:
    out = src.replace(old, new)
else:
    if "[zabbix-alert-call]" in src:
        raise SystemExit("Found zabbix-alert-call with unexpected body; aborting")
    out = src.rstrip() + "\n\n" + new

target.write_text(out, encoding="utf-8")
PY

cp -a "$cfg" "${cfg}.bak_$(date +%Y%m%d_%H%M%S)"
cp "$tmp" "$cfg"
rm -f "$tmp"

asterisk -rx "dialplan reload"
asterisk -rx "dialplan show zabbix-alert-call"
