#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: main-branch-lock.sh run --owner <name> [--timeout-seconds <seconds>] -- <command> [args...]
USAGE
  exit 64
}

if [[ $# -lt 1 || "${1:-}" != "run" ]]; then
  usage
fi
shift

owner=""
timeout_seconds=3600
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      [[ $# -ge 2 ]] || usage
      owner="$2"
      shift 2
      ;;
    --timeout-seconds)
      [[ $# -ge 2 ]] || usage
      timeout_seconds="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$owner" && $# -gt 0 ]] || usage
[[ "$timeout_seconds" =~ ^[0-9]+$ ]] || usage

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if project_root="$(git -C "$script_dir/../.." rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  project_root="$(cd "$script_dir/../.." && pwd)"
fi
locks_dir="$project_root/.agents/locks"
lock_dir="$locks_dir/main-branch.lock"
metadata_file="$lock_dir/metadata"
host="$(hostname)"
pid="$$"
started_at="$(date +%s)"
acquired=0

mkdir -p "$locks_dir"

read_metadata_value() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key { print substr($0, length(key) + 2); exit }' "$metadata_file" 2>/dev/null || true
}

write_metadata() {
  {
    printf 'owner=%s\n' "$owner"
    printf 'pid=%s\n' "$pid"
    printf 'host=%s\n' "$host"
    printf 'created_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'project_root=%s\n' "$project_root"
    printf 'command=%q' "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  } > "$metadata_file"
}

cleanup() {
  if [[ "$acquired" -eq 1 ]]; then
    local locked_pid locked_host
    locked_pid="$(read_metadata_value pid)"
    locked_host="$(read_metadata_value host)"
    if [[ "$locked_pid" == "$pid" && "$locked_host" == "$host" ]]; then
      rm -rf "$lock_dir"
    fi
  fi
}

trap cleanup EXIT INT TERM

while true; do
  if mkdir "$lock_dir" 2>/dev/null; then
    acquired=1
    write_metadata "$@"
    "$@"
    exit $?
  fi

  locked_pid="$(read_metadata_value pid)"
  locked_host="$(read_metadata_value host)"
  if [[ "$locked_host" == "$host" && "$locked_pid" =~ ^[0-9]+$ ]]; then
    if ! kill -0 "$locked_pid" 2>/dev/null; then
      rm -rf "$lock_dir"
      continue
    fi
  fi

  now="$(date +%s)"
  if (( now - started_at >= timeout_seconds )); then
    echo "Timed out waiting for main branch lock: $lock_dir" >&2
    if [[ -f "$metadata_file" ]]; then
      echo "Current lock metadata:" >&2
      cat "$metadata_file" >&2
    fi
    exit 75
  fi

  sleep 2
done
