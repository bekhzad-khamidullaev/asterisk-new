#!/usr/bin/env bash
set -euo pipefail

# Deploy dispatch page as native Zabbix action/view (app/*), while keeping
# classic problem.view intact.
#
# Usage:
#   sudo bash scripts/deploy_dispatch_native.sh
#   ZBX_ROOT=/usr/share/zabbix sudo bash scripts/deploy_dispatch_native.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ZBX_ROOT="${ZBX_ROOT:-/usr/share/zabbix}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${ZBX_ROOT}/backup_dispatch_native_${STAMP}"

require_file() {
	local file="$1"
	if [[ ! -f "$file" ]]; then
		echo "ERROR: required file not found: $file" >&2
		exit 1
	fi
}

require_file "${REPO_ROOT}/tmp/CControllerProblemDispatchView.php"
require_file "${REPO_ROOT}/tmp/CControllerProblemDispatchViewRefresh.php"
require_file "${REPO_ROOT}/tmp/CControllerReportDispatchApi.php"
require_file "${REPO_ROOT}/tmp/monitoring.problem.dispatch.view.php"
require_file "${REPO_ROOT}/tmp/CRouter.php"

for d in "${ZBX_ROOT}" "${ZBX_ROOT}/app" "${ZBX_ROOT}/include/classes/mvc"; do
	if [[ ! -d "$d" ]]; then
		echo "ERROR: Zabbix path not found: $d" >&2
		exit 1
	fi
done

echo "Deploying to: ${ZBX_ROOT}"
mkdir -p "${BACKUP_DIR}/app/controllers" "${BACKUP_DIR}/app/views" "${BACKUP_DIR}/include/classes/mvc"

backup_if_exists() {
	local src="$1"
	local dst="$2"
	if [[ -f "$src" ]]; then
		cp -a "$src" "$dst"
	fi
}

backup_if_exists "${ZBX_ROOT}/app/controllers/CControllerProblemDispatchView.php" \
	"${BACKUP_DIR}/app/controllers/CControllerProblemDispatchView.php"
backup_if_exists "${ZBX_ROOT}/app/controllers/CControllerProblemDispatchViewRefresh.php" \
	"${BACKUP_DIR}/app/controllers/CControllerProblemDispatchViewRefresh.php"
backup_if_exists "${ZBX_ROOT}/app/controllers/CControllerReportDispatchApi.php" \
	"${BACKUP_DIR}/app/controllers/CControllerReportDispatchApi.php"
backup_if_exists "${ZBX_ROOT}/app/views/monitoring.problem.dispatch.view.php" \
	"${BACKUP_DIR}/app/views/monitoring.problem.dispatch.view.php"
backup_if_exists "${ZBX_ROOT}/include/classes/mvc/CRouter.php" \
	"${BACKUP_DIR}/include/classes/mvc/CRouter.php"

install -m 0644 "${REPO_ROOT}/tmp/CControllerProblemDispatchView.php" \
	"${ZBX_ROOT}/app/controllers/CControllerProblemDispatchView.php"
install -m 0644 "${REPO_ROOT}/tmp/CControllerProblemDispatchViewRefresh.php" \
	"${ZBX_ROOT}/app/controllers/CControllerProblemDispatchViewRefresh.php"
install -m 0644 "${REPO_ROOT}/tmp/CControllerReportDispatchApi.php" \
	"${ZBX_ROOT}/app/controllers/CControllerReportDispatchApi.php"
install -m 0644 "${REPO_ROOT}/tmp/monitoring.problem.dispatch.view.php" \
	"${ZBX_ROOT}/app/views/monitoring.problem.dispatch.view.php"
install -m 0644 "${REPO_ROOT}/tmp/CRouter.php" \
	"${ZBX_ROOT}/include/classes/mvc/CRouter.php"

if [[ -d "${ZBX_ROOT}/local/app/controllers" ]]; then
	rm -f "${ZBX_ROOT}/local/app/controllers/CControllerProblemDispatchView.php" \
		"${ZBX_ROOT}/local/app/controllers/CControllerProblemDispatchViewRefresh.php" \
		"${ZBX_ROOT}/local/app/controllers/CControllerReportDispatchApi.php"
fi

if [[ -d "${ZBX_ROOT}/local/app/views" ]]; then
	rm -f "${ZBX_ROOT}/local/app/views/monitoring.problem.dispatch.view.php"
fi

php -l "${ZBX_ROOT}/app/controllers/CControllerProblemDispatchView.php" >/dev/null
php -l "${ZBX_ROOT}/app/controllers/CControllerProblemDispatchViewRefresh.php" >/dev/null
php -l "${ZBX_ROOT}/app/controllers/CControllerReportDispatchApi.php" >/dev/null
php -l "${ZBX_ROOT}/app/views/monitoring.problem.dispatch.view.php" >/dev/null
php -l "${ZBX_ROOT}/include/classes/mvc/CRouter.php" >/dev/null

echo "OK: native dispatch deployed."
echo "Backup: ${BACKUP_DIR}"
echo "Next: hard refresh browser (Ctrl+F5) and open:"
echo "  zabbix.php?action=problem.dispatch.view"
