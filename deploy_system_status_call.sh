#!/usr/bin/env bash
set -euo pipefail

if ! grep -qF "[system-status-call]" /etc/asterisk/extensions.conf; then
  cp -a /etc/asterisk/extensions.conf "/etc/asterisk/extensions.conf.bak_$(date +%Y%m%d_%H%M%S)"
  printf "\n" >> /etc/asterisk/extensions.conf
  cat /tmp/system-status-call.context >> /etc/asterisk/extensions.conf
fi

asterisk -rx "dialplan reload"
asterisk -rx "dialplan show system-status-call"
