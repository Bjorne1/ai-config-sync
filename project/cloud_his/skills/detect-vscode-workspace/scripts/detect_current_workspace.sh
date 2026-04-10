#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_ROOT="/home/wcs/projects/work-project/cloud_his"
readonly SERVICE_REGEX="ai-service|drg-service|emr-service|his-service|interface-service|pay-service|report-service|xxl-job-admin"
readonly MODE_FULL="full"
readonly MODE_PATH_ONLY="path_only"
readonly MODE_CONTENT_ONLY="content_only"

MODE="${MODE_FULL}"

fail() {
  echo "$*" >&2
  exit 1
}

print_usage() {
  cat <<'EOF'
Usage:
  detect_current_workspace.sh
  detect_current_workspace.sh --path-only
  detect_current_workspace.sh --content-only

This script resolves the VSCode workspace bound to the current Codex conversation window.
EOF
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --path-only)
        MODE="${MODE_PATH_ONLY}"
        shift
        ;;
      --content-only)
        MODE="${MODE_CONTENT_ONLY}"
        shift
        ;;
      --help|-h)
        print_usage
        exit 0
        ;;
      *)
        fail "Unsupported option: $1"
        ;;
    esac
  done
}

ps_command() {
  ps -o command= -p "$1" 2>/dev/null | sed 's/^[[:space:]]*//'
}

ps_ppid() {
  ps -o ppid= -p "$1" 2>/dev/null | tr -d ' '
}

find_extension_host_pid_from_ancestry() {
  local pid="${PPID:-}"
  local cmd=""
  while [[ -n "${pid}" && "${pid}" != "0" && "${pid}" != "1" ]]; do
    cmd="$(ps_command "${pid}")"
    [[ -n "${cmd}" ]] || break
    if [[ "${cmd}" == *"--type=extensionHost"* ]]; then
      printf '%s\n' "${pid}"
      return 0
    fi
    pid="$(ps_ppid "${pid}")"
  done
  return 1
}

find_extension_host_pid_from_ipc() {
  local pid=""
  local cmd=""

  [[ -n "${VSCODE_IPC_HOOK_CLI:-}" ]] || return 1
  pid="$(lsof -t "${VSCODE_IPC_HOOK_CLI}" 2>/dev/null | head -n1 || true)"
  [[ -n "${pid}" ]] || return 1

  cmd="$(ps_command "${pid}")"
  if [[ "${cmd}" == *"--type=extensionHost"* ]]; then
    printf '%s\n' "${pid}"
    return 0
  fi

  return 1
}

find_extension_host_pid() {
  local pid=""
  pid="$(find_extension_host_pid_from_ancestry || true)"
  if [[ -n "${pid}" ]]; then
    printf '%s\n' "${pid}"
    return 0
  fi

  pid="$(find_extension_host_pid_from_ipc || true)"
  if [[ -n "${pid}" ]]; then
    printf '%s\n' "${pid}"
    return 0
  fi

  fail "Unable to locate current VSCode extensionHost"
}

extract_remote_log_path() {
  local extension_host_pid="$1"
  lsof -p "${extension_host_pid}" 2>/dev/null \
    | awk 'NR > 1 {print $NF}' \
    | rg '/remoteexthost\.log$' \
    | head -n1
}

extract_workspace_storage_from_lsof() {
  local extension_host_pid="$1"
  local candidates=()

  mapfile -t candidates < <(
    lsof -p "${extension_host_pid}" 2>/dev/null \
      | awk 'NR > 1 {print $NF}' \
      | sed -n 's#^\(.*/workspaceStorage/[^/]*\)/.*#\1#p' \
      | sort -u
  )

  if [[ "${#candidates[@]}" -eq 1 ]]; then
    printf '%s\n' "${candidates[0]}"
    return 0
  fi

  if [[ "${#candidates[@]}" -gt 1 ]]; then
    fail "Unable to resolve unique workspaceStorage from extensionHost open files"
  fi

  return 1
}

extract_workspace_storage_from_remote_log() {
  local remote_log="$1"
  rg "Lock '.*workspaceStorage/.*/vscode\\.lock': Lock acquired\\." "${remote_log}" 2>/dev/null \
    | tail -n1 \
    | sed -E "s#.*Lock '(.*/workspaceStorage/[^/]+/vscode\\.lock)'.*#\\1#" \
    | sed 's#/vscode.lock$##'
}

resolve_workspace_storage_dir() {
  local extension_host_pid="$1"
  local remote_log="$2"
  local from_lsof=""
  local from_remote=""

  from_lsof="$(extract_workspace_storage_from_lsof "${extension_host_pid}" || true)"
  from_remote="$(extract_workspace_storage_from_remote_log "${remote_log}" || true)"

  if [[ -n "${from_lsof}" && -n "${from_remote}" && "${from_lsof}" != "${from_remote}" ]]; then
    fail "Unable to resolve unique workspaceStorage: extensionHost and remote log disagree"
  fi

  if [[ -n "${from_lsof}" ]]; then
    printf '%s\n' "${from_lsof}"
    return 0
  fi

  if [[ -n "${from_remote}" ]]; then
    printf '%s\n' "${from_remote}"
    return 0
  fi

  fail "Unable to resolve unique workspaceStorage"
}

service_from_deps_files() {
  local workspace_storage_dir="$1"
  local deps_dir="${workspace_storage_dir}/vscjava.vscode-maven"
  local candidates=()
  local file=""

  [[ -d "${deps_dir}" ]] || return 1

  shopt -s nullglob
  mapfile -t candidates < <(
    for file in "${deps_dir}"/*.deps.txt; do
      sed -n '1s/^com\.whxx:\([a-z0-9-]\+\):.*/\1/p' "${file}"
    done | sort -u
  )
  shopt -u nullglob

  if [[ "${#candidates[@]}" -eq 1 ]]; then
    printf '%s\n' "${candidates[0]}"
    return 0
  fi

  if [[ "${#candidates[@]}" -gt 1 ]]; then
    fail "Unable to resolve unique service from workspaceStorage dependency files"
  fi

  return 1
}

collect_service_hint_files() {
  local workspace_storage_dir="$1"
  local remote_log="$2"
  local remote_dir=""

  if [[ -d "${workspace_storage_dir}/redhat.java" ]]; then
    find "${workspace_storage_dir}/redhat.java" -maxdepth 1 -type f -name 'client.log*'
  fi

  printf '%s\n' "${remote_log}"
  remote_dir="$(dirname "${remote_log}")"

  if [[ -d "${remote_dir}/vscode.git" ]]; then
    find "${remote_dir}/vscode.git" -maxdepth 1 -type f -name '*.log'
  fi

  find "${remote_dir}" -maxdepth 3 -type f -path '*/output_logging_*/*.log'
}

service_from_logs() {
  local workspace_storage_dir="$1"
  local remote_log="$2"
  local files=()
  local candidates=()
  local file=""

  mapfile -t files < <(collect_service_hint_files "${workspace_storage_dir}" "${remote_log}" | awk 'NF' | sort -u)
  [[ "${#files[@]}" -gt 0 ]] || return 1

  mapfile -t candidates < <(
    rg -h -o "com\\.whxx:${SERVICE_REGEX}|\\[in ${SERVICE_REGEX}\\]|wh-modules/${SERVICE_REGEX}/" "${files[@]}" 2>/dev/null \
      | sed -E 's#com\.whxx:##; s#\[in ##; s#\]##; s#wh-modules/##; s#/$##' \
      | sort -u
  )

  if [[ "${#candidates[@]}" -eq 1 ]]; then
    printf '%s\n' "${candidates[0]}"
    return 0
  fi

  if [[ "${#candidates[@]}" -gt 1 ]]; then
    fail "Unable to resolve unique service from current window logs"
  fi

  return 1
}

resolve_service_name() {
  local workspace_storage_dir="$1"
  local remote_log="$2"
  local service=""

  service="$(service_from_deps_files "${workspace_storage_dir}" || true)"
  if [[ -n "${service}" ]]; then
    printf '%s\n' "${service}"
    return 0
  fi

  service="$(service_from_logs "${workspace_storage_dir}" "${remote_log}" || true)"
  if [[ -n "${service}" ]]; then
    printf '%s\n' "${service}"
    return 0
  fi

  fail "Unable to resolve unique service"
}

resolve_workspace_file() {
  local service_name="$1"
  local workspace_file="${PROJECT_ROOT}/${service_name}-dev.code-workspace"
  [[ -f "${workspace_file}" ]] || fail "Workspace file not found: ${workspace_file}"
  printf '%s\n' "${workspace_file}"
}

print_result() {
  local extension_host_pid="$1"
  local remote_log="$2"
  local workspace_storage_dir="$3"
  local service_name="$4"
  local workspace_file="$5"

  case "${MODE}" in
    "${MODE_PATH_ONLY}")
      printf '%s\n' "${workspace_file}"
      ;;
    "${MODE_CONTENT_ONLY}")
      cat "${workspace_file}"
      ;;
    *)
      cat <<EOF
Extension host PID: ${extension_host_pid}
Remote log: ${remote_log}
Workspace storage: ${workspace_storage_dir}
Resolved service: ${service_name}
Workspace file: ${workspace_file}

Workspace file content:
EOF
      cat "${workspace_file}"
      ;;
  esac
}

main() {
  local extension_host_pid=""
  local remote_log=""
  local workspace_storage_dir=""
  local service_name=""
  local workspace_file=""

  require_command ps
  require_command lsof
  require_command rg
  require_command sed
  require_command awk
  require_command find

  parse_args "$@"

  extension_host_pid="$(find_extension_host_pid)"
  remote_log="$(extract_remote_log_path "${extension_host_pid}" || true)"
  [[ -n "${remote_log}" && -f "${remote_log}" ]] || fail "Unable to locate current remoteexthost.log"

  workspace_storage_dir="$(resolve_workspace_storage_dir "${extension_host_pid}" "${remote_log}")"
  [[ -d "${workspace_storage_dir}" ]] || fail "Resolved workspaceStorage does not exist: ${workspace_storage_dir}"

  service_name="$(resolve_service_name "${workspace_storage_dir}" "${remote_log}")"
  workspace_file="$(resolve_workspace_file "${service_name}")"

  print_result "${extension_host_pid}" "${remote_log}" "${workspace_storage_dir}" "${service_name}" "${workspace_file}"
}

main "$@"
