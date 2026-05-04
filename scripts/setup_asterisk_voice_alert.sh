#!/usr/bin/env bash
set -euo pipefail

# Setup Asterisk side for Zabbix voice alerts (AMI + edge-tts AGI + dialplan)
# Run on tshttaster as root.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

AGI_BIN="${AGI_BIN:-/var/lib/asterisk/agi-bin}"
EXTENSIONS_CONF="${EXTENSIONS_CONF:-/etc/asterisk/extensions.conf}"
MANAGER_CONF="${MANAGER_CONF:-/etc/asterisk/manager.conf}"
AMI_USER="${AMI_USER:-zabbix_call}"
AMI_SECRET="${AMI_SECRET:-CHANGE_ME_STRONG_SECRET}"
ZBX_IP="${ZBX_IP:-127.0.0.1}"

if [[ "$AMI_SECRET" == "CHANGE_ME_STRONG_SECRET" ]]; then
  echo "ERROR: set AMI_SECRET env var" >&2
  exit 1
fi

for f in "${REPO_ROOT}/scripts/zabbix_tts_alert.py" "${REPO_ROOT}/zabbix-alert-call.context"; do
  [[ -f "$f" ]] || { echo "Missing file: $f" >&2; exit 1; }
done

if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y sox python3-pip
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y sox python3-pip
elif command -v yum >/dev/null 2>&1; then
  yum install -y sox python3-pip
fi

python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install --upgrade edge-tts

mkdir -p "${AGI_BIN}"
install -m 0755 "${REPO_ROOT}/scripts/zabbix_tts_alert.py" "${AGI_BIN}/zabbix_tts_alert.py"
mkdir -p /var/lib/asterisk/sounds/zabbix-alert/cache
chown -R asterisk:asterisk /var/lib/asterisk/sounds/zabbix-alert || true

python3 - "$EXTENSIONS_CONF" "${REPO_ROOT}/zabbix-alert-call.context" <<'PY'
import re
import sys
from pathlib import Path

ext = Path(sys.argv[1])
ctx = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip() + "\n"
text = ext.read_text(encoding="utf-8") if ext.exists() else ""
pat = re.compile(r"(?ms)^\[zabbix-alert-call\]\n.*?(?=^\[|\Z)")
if pat.search(text):
    out = pat.sub(ctx + "\n", text)
else:
    if text and not text.endswith("\n"):
        text += "\n"
    out = text + "\n" + ctx + "\n"
ext.write_text(out, encoding="utf-8")
PY

python3 - "$MANAGER_CONF" "$AMI_USER" "$AMI_SECRET" "$ZBX_IP" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
user = sys.argv[2]
secret = sys.argv[3]
zbx_ip = sys.argv[4]

block = f"""[{user}]
secret = {secret}
read = none
write = originate
permit = {zbx_ip}/255.255.255.255
deny = 0.0.0.0/0.0.0.0

"""
text = path.read_text(encoding="utf-8") if path.exists() else ""
pat = re.compile(rf"(?ms)^\[{re.escape(user)}\]\n.*?(?=^\[|\Z)")
if pat.search(text):
    out = pat.sub(block, text)
else:
    if text and not text.endswith("\n"):
        text += "\n"
    out = text + "\n" + block
path.write_text(out, encoding="utf-8")
PY

asterisk -rx "manager reload" || true
asterisk -rx "dialplan reload" || true
asterisk -rx "dialplan show zabbix-alert-call" || true

echo "Asterisk setup completed"
