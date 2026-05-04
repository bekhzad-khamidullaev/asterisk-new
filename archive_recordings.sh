#!/usr/bin/env bash
set -euo pipefail

MONITOR_ROOT=${MONITOR_ROOT:-/var/spool/asterisk/monitor}
ARCHIVE_ROOT=${ARCHIVE_ROOT:-/var/spool/asterisk/record_backups}
RETENTION_MONTHS=${RETENTION_MONTHS:-3}
LOG_PREFIX="[recording-archive]"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

log() {
  printf '%s %s\n' "$LOG_PREFIX" "$*"
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "dry-run: $*"
    return 0
  fi
  "$@"
}

month_threshold_ym() {
  date -d "$(date +%Y-%m-01) -$((RETENTION_MONTHS - 1)) months" +%Y%m
}

archive_month() {
  local year=$1
  local month=$2
  local month_dir="${MONITOR_ROOT}/${year}/${month}"
  local month_key="${year}-${month}"
  local backup_dir="${ARCHIVE_ROOT}/${month_key}"
  local final_archive="${backup_dir}/archive_${month_key}.tar.gz"
  local temp_archive="${final_archive}.tmp"

  if [[ ! -d "$month_dir" ]]; then
    return 0
  fi

  if ! find "$month_dir" -type f -print -quit | grep -q .; then
    log "skip empty month ${month_key}"
    return 0
  fi

  if [[ -f "$final_archive" ]]; then
    log "archive already exists for ${month_key}, skip to avoid overwrite"
    return 0
  fi

  run mkdir -p "$backup_dir"
  log "archiving ${month_key} from ${month_dir} to ${final_archive}"

  if [[ "$DRY_RUN" -eq 0 ]]; then
    tar -C "$month_dir" -czf "$temp_archive" .
    tar -tzf "$temp_archive" >/dev/null
    mv "$temp_archive" "$final_archive"
    sha256sum "$final_archive" > "${final_archive}.sha256"

    find "$month_dir" -type f -delete
    find "$month_dir" -depth -type d -empty -delete
    log "archive completed and source files removed for ${month_key}"
  fi
}

main() {
  local keep_from
  keep_from=$(month_threshold_ym)

  run mkdir -p "$ARCHIVE_ROOT"
  log "retention months=${RETENTION_MONTHS}, archive months older than ${keep_from}"

  while IFS= read -r -d '' year_dir; do
    local year
    year=$(basename "$year_dir")
    [[ "$year" =~ ^[0-9]{4}$ ]] || continue

    while IFS= read -r -d '' month_dir; do
      local month ym
      month=$(basename "$month_dir")
      [[ "$month" =~ ^[0-9]{2}$ ]] || continue
      ym="${year}${month}"

      if [[ "$ym" < "$keep_from" ]]; then
        archive_month "$year" "$month"
      fi
    done < <(find "$year_dir" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
  done < <(find "$MONITOR_ROOT" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
}

main "$@"
