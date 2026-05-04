#!/usr/bin/env bash
set -euo pipefail

# One-shot deployment to both servers over SSH.
# Requires SSH access and sudo rights.

TSHTTZBX_HOST="${TSHTTZBX_HOST:-tshttzbx}"
TSHTTASTER_HOST="${TSHTTASTER_HOST:-tshttaster}"
TSHTTZBX_USER="${TSHTTZBX_USER:-root}"
TSHTTASTER_USER="${TSHTTASTER_USER:-root}"
AMI_SECRET="${AMI_SECRET:-}"
ZBX_IP_FOR_AMI="${ZBX_IP_FOR_AMI:-}"

if [[ -z "$AMI_SECRET" ]]; then
  echo "ERROR: export AMI_SECRET before running" >&2
  exit 1
fi
if [[ -z "$ZBX_IP_FOR_AMI" ]]; then
  echo "ERROR: export ZBX_IP_FOR_AMI before running" >&2
  exit 1
fi

WORKDIR_REMOTE="/tmp/zbx_voice_alert_stack"

copy_bundle() {
  local host="$1"
  local user="$2"
  ssh "${user}@${host}" "mkdir -p ${WORKDIR_REMOTE}/scripts"
  scp scripts/zbxAsteriskCall.py "${user}@${host}:${WORKDIR_REMOTE}/scripts/"
  scp scripts/zabbix_tts_alert.py "${user}@${host}:${WORKDIR_REMOTE}/scripts/"
  scp scripts/setup_asterisk_voice_alert.sh "${user}@${host}:${WORKDIR_REMOTE}/scripts/"
  scp scripts/setup_zabbix_voice_alert.sh "${user}@${host}:${WORKDIR_REMOTE}/scripts/"
  scp zabbix-alert-call.context "${user}@${host}:${WORKDIR_REMOTE}/"
}

copy_bundle "$TSHTTASTER_HOST" "$TSHTTASTER_USER"
copy_bundle "$TSHTTZBX_HOST" "$TSHTTZBX_USER"

ssh "${TSHTTASTER_USER}@${TSHTTASTER_HOST}" \
  "chmod +x ${WORKDIR_REMOTE}/scripts/setup_asterisk_voice_alert.sh && \
   AMI_SECRET='${AMI_SECRET}' ZBX_IP='${ZBX_IP_FOR_AMI}' ${WORKDIR_REMOTE}/scripts/setup_asterisk_voice_alert.sh"

ssh "${TSHTTZBX_USER}@${TSHTTZBX_HOST}" \
  "chmod +x ${WORKDIR_REMOTE}/scripts/setup_zabbix_voice_alert.sh && \
   ${WORKDIR_REMOTE}/scripts/setup_zabbix_voice_alert.sh"

echo "Deployment to servers completed."
echo "Next: run configure_zabbix_voice_alert.py against Zabbix API."
