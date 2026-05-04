#!/usr/bin/env bash
set -euo pipefail

# Setup Zabbix script side. Run on tshttzbx as root.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ALERTSCRIPTS_PATH="${ALERTSCRIPTS_PATH:-/usr/lib/zabbix/alertscripts}"

SRC="${REPO_ROOT}/scripts/zbxAsteriskCall.py"
[[ -f "$SRC" ]] || { echo "Missing file: $SRC" >&2; exit 1; }

mkdir -p "$ALERTSCRIPTS_PATH"
install -m 0755 "$SRC" "$ALERTSCRIPTS_PATH/zbxAsteriskCall.py"

if command -v zabbix_server >/dev/null 2>&1; then
  zabbix_server -V >/dev/null 2>&1 || true
fi

echo "Installed: $ALERTSCRIPTS_PATH/zbxAsteriskCall.py"
echo "Ensure zabbix_server.conf has AlertScriptsPath=$ALERTSCRIPTS_PATH"
