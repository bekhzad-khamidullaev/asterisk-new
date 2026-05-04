#!/usr/bin/env bash
set -euo pipefail

# Deploy Zabbix -> Asterisk voice alert integration files.
# Usage example:
#   sudo bash scripts/deploy_zabbix_voice_alert_stack.sh \
#     --zbx-alertscripts /usr/lib/zabbix/alertscripts \
#     --agi-bin /var/lib/asterisk/agi-bin \
#     --extensions /etc/asterisk/extensions.conf

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ZBX_ALERTSCRIPTS="/usr/lib/zabbix/alertscripts"
AGI_BIN="/var/lib/asterisk/agi-bin"
EXTENSIONS_CONF="/etc/asterisk/extensions.conf"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zbx-alertscripts)
      ZBX_ALERTSCRIPTS="$2"; shift 2;;
    --agi-bin)
      AGI_BIN="$2"; shift 2;;
    --extensions)
      EXTENSIONS_CONF="$2"; shift 2;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1;;
  esac
done

if [[ ! -f "${REPO_ROOT}/scripts/zbxAsteriskCall.py" ]]; then
  echo "Missing source script: ${REPO_ROOT}/scripts/zbxAsteriskCall.py" >&2
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/scripts/zabbix_tts_alert.py" ]]; then
  echo "Missing source script: ${REPO_ROOT}/scripts/zabbix_tts_alert.py" >&2
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/zabbix-alert-call.context" ]]; then
  echo "Missing context file: ${REPO_ROOT}/zabbix-alert-call.context" >&2
  exit 1
fi

mkdir -p "${ZBX_ALERTSCRIPTS}" "${AGI_BIN}"
install -m 0755 "${REPO_ROOT}/scripts/zbxAsteriskCall.py" "${ZBX_ALERTSCRIPTS}/zbxAsteriskCall.py"
install -m 0755 "${REPO_ROOT}/scripts/zabbix_tts_alert.py" "${AGI_BIN}/zabbix_tts_alert.py"

echo "Installed scripts:"
echo " - ${ZBX_ALERTSCRIPTS}/zbxAsteriskCall.py"
echo " - ${AGI_BIN}/zabbix_tts_alert.py"

python3 - "$EXTENSIONS_CONF" "${REPO_ROOT}/zabbix-alert-call.context" <<'PY'
import re
import sys
from pathlib import Path

extensions = Path(sys.argv[1])
context = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip() + "\n"

if not extensions.exists():
    raise SystemExit(f"extensions.conf not found: {extensions}")

text = extensions.read_text(encoding="utf-8")
pattern = re.compile(r"(?ms)^\[zabbix-alert-call\]\n.*?(?=^\[|\Z)")

if pattern.search(text):
    out = pattern.sub(context + "\n", text)
    mode = "updated"
else:
    if not text.endswith("\n"):
        text += "\n"
    out = text + "\n" + context + "\n"
    mode = "appended"

extensions.write_text(out, encoding="utf-8")
print(mode)
PY

if command -v asterisk >/dev/null 2>&1; then
  asterisk -rx "dialplan reload" || true
  asterisk -rx "dialplan show zabbix-alert-call" || true
fi

echo "Dialplan section [zabbix-alert-call] installed in ${EXTENSIONS_CONF}."
echo "Next steps:"
echo "  1) Configure AMI user [zabbix_call] in /etc/asterisk/manager.conf"
echo "  2) Install dependencies on tshttaster: python3 -m pip install edge-tts && apt/yum install sox"
echo "  3) Configure Zabbix media type as documented in ZABBIX_ASTERISK_CALL_INTEGRATION.md"
