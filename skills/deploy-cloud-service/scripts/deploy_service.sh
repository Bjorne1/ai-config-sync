#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_ROOT="/home/wcs/projects/work-project/cloud_his"
readonly JAVA_HOME_DIR="/home/wcs/.local/opt/jdk8"
readonly DEPLOY_DIR="/mnt/e/deploy-project"
readonly DRY_RUN_ENABLED="1"
readonly DRY_RUN_DISABLED="0"

print_usage() {
  cat <<'EOF'
Usage:
  deploy_service.sh [service]
  deploy_service.sh --workspace-file <workspace>
  deploy_service.sh --dry-run [service]
  deploy_service.sh --list-services

Service aliases:
  ai drg emr his interface pay report xxl

Resolution order:
  1. Explicit service argument
  2. Current working directory under wh-modules/<service>
  3. --workspace-file mapping, only when caller already knows the active workspace file

This script does not scan repository *.code-workspace files.
EOF
}

print_supported_services() {
  cat <<'EOF'
ai -> ai-service
drg -> drg-service
emr -> emr-service
his -> his-service
interface -> interface-service
pay -> pay-service
report -> report-service
xxl -> xxl-job-admin
EOF
}

normalize_service_name() {
  case "${1}" in
    ai|ai-service) printf '%s\n' "ai-service" ;;
    drg|drg-service) printf '%s\n' "drg-service" ;;
    emr|emr-service) printf '%s\n' "emr-service" ;;
    his|his-service) printf '%s\n' "his-service" ;;
    interface|interface-service) printf '%s\n' "interface-service" ;;
    pay|pay-service) printf '%s\n' "pay-service" ;;
    report|report-service) printf '%s\n' "report-service" ;;
    xxl|xxl-job-admin) printf '%s\n' "xxl-job-admin" ;;
    *) return 1 ;;
  esac
}

service_from_workspace() {
  local workspace_name
  workspace_name="$(basename "$1")"
  case "${workspace_name}" in
    ai-service-dev.code-workspace) printf '%s\n' "ai-service" ;;
    drg-service-dev.code-workspace) printf '%s\n' "drg-service" ;;
    emr-service-dev.code-workspace) printf '%s\n' "emr-service" ;;
    his-service-dev.code-workspace) printf '%s\n' "his-service" ;;
    *) return 1 ;;
  esac
}

service_from_cwd() {
  case "${1}" in
    "${PROJECT_ROOT}/wh-modules/ai-service"|\
    "${PROJECT_ROOT}/wh-modules/ai-service"/*) printf '%s\n' "ai-service" ;;
    "${PROJECT_ROOT}/wh-modules/drg-service"|\
    "${PROJECT_ROOT}/wh-modules/drg-service"/*) printf '%s\n' "drg-service" ;;
    "${PROJECT_ROOT}/wh-modules/emr-service"|\
    "${PROJECT_ROOT}/wh-modules/emr-service"/*) printf '%s\n' "emr-service" ;;
    "${PROJECT_ROOT}/wh-modules/his-service"|\
    "${PROJECT_ROOT}/wh-modules/his-service"/*) printf '%s\n' "his-service" ;;
    "${PROJECT_ROOT}/wh-modules/interface-service"|\
    "${PROJECT_ROOT}/wh-modules/interface-service"/*) printf '%s\n' "interface-service" ;;
    "${PROJECT_ROOT}/wh-modules/pay-service"|\
    "${PROJECT_ROOT}/wh-modules/pay-service"/*) printf '%s\n' "pay-service" ;;
    "${PROJECT_ROOT}/wh-modules/report-service"|\
    "${PROJECT_ROOT}/wh-modules/report-service"/*) printf '%s\n' "report-service" ;;
    "${PROJECT_ROOT}/wh-modules/xxl-job-admin"|\
    "${PROJECT_ROOT}/wh-modules/xxl-job-admin"/*) printf '%s\n' "xxl-job-admin" ;;
    *) return 1 ;;
  esac
}

service_config() {
  case "${1}" in
    ai-service) printf '%s\n' "wh-modules/ai-service|ai-service.jar" ;;
    drg-service) printf '%s\n' "wh-modules/drg-service|drg-service.jar" ;;
    emr-service) printf '%s\n' "wh-modules/emr-service|emr-service.jar" ;;
    his-service) printf '%s\n' "wh-modules/his-service|his-service.jar" ;;
    interface-service) printf '%s\n' "wh-modules/interface-service|his-interface-service.jar" ;;
    pay-service) printf '%s\n' "wh-modules/pay-service|pay-service.jar" ;;
    report-service) printf '%s\n' "wh-modules/report-service|report-service.jar" ;;
    xxl-job-admin) printf '%s\n' "wh-modules/xxl-job-admin|xxljob-service.jar" ;;
    *) return 1 ;;
  esac
}

resolve_service() {
  local explicit_service="$1"
  local workspace_file="$2"
  local current_dir="$3"

  if [[ -n "${explicit_service}" ]]; then
    normalize_service_name "${explicit_service}"
    return 0
  fi

  if [[ -n "${workspace_file}" ]]; then
    service_from_workspace "${workspace_file}"
    return 0
  fi

  service_from_cwd "${current_dir}"
}

parse_args() {
  DRY_RUN="${DRY_RUN_DISABLED}"
  WORKSPACE_FILE=""
  EXPLICIT_SERVICE=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        DRY_RUN="${DRY_RUN_ENABLED}"
        shift
        ;;
      --workspace-file)
        [[ $# -ge 2 ]] || {
          echo "Missing value for --workspace-file" >&2
          exit 1
        }
        WORKSPACE_FILE="$2"
        shift 2
        ;;
      --list-services)
        print_supported_services
        exit 0
        ;;
      --help|-h)
        print_usage
        exit 0
        ;;
      -*)
        echo "Unsupported option: $1" >&2
        exit 1
        ;;
      *)
        [[ -z "${EXPLICIT_SERVICE}" ]] || {
          echo "Only one service argument is allowed" >&2
          exit 1
        }
        EXPLICIT_SERVICE="$1"
        shift
        ;;
    esac
  done
}

print_execution_plan() {
  local resolved_service="$1"
  local module_path="$2"
  local artifact_path="$3"
  local deploy_path="$4"
  shift 4
  local mvn_cmd=("$@")

  echo "Resolved service: ${resolved_service}"
  echo "Module path: ${module_path}"
  echo "Artifact path: ${artifact_path}"
  echo "Deploy path: ${deploy_path}"
  printf 'Maven command: JAVA_HOME=%s PATH=%s/bin:$PATH ' "${JAVA_HOME_DIR}" "${JAVA_HOME_DIR}"
  printf '%q ' "${mvn_cmd[@]}"
  printf '\n'
}

run_deploy() {
  local artifact_path="$1"
  local deploy_path="$2"
  shift 2
  local mvn_cmd=("$@")

  [[ -d "${DEPLOY_DIR}" ]] || {
    echo "Deploy directory does not exist: ${DEPLOY_DIR}" >&2
    exit 1
  }

  export JAVA_HOME="${JAVA_HOME_DIR}"
  export PATH="${JAVA_HOME}/bin:${PATH}"

  (
    cd "${PROJECT_ROOT}"
    "${mvn_cmd[@]}"
  )

  [[ -f "${artifact_path}" ]] || {
    echo "Artifact not found after build: ${artifact_path}" >&2
    exit 1
  }

  cp -f "${artifact_path}" "${deploy_path}"
  echo "Copied artifact to: ${deploy_path}"
}

main() {
  parse_args "$@"

  local resolved_service
  resolved_service="$(resolve_service "${EXPLICIT_SERVICE}" "${WORKSPACE_FILE}" "${PWD}")" || {
    echo "Unable to resolve target service. Specify ai|drg|emr|his|interface|pay|report|xxl explicitly." >&2
    exit 1
  }

  local config
  config="$(service_config "${resolved_service}")"

  local module_path artifact_name
  IFS='|' read -r module_path artifact_name <<< "${config}"

  local artifact_path="${PROJECT_ROOT}/${module_path}/target/${artifact_name}"
  local deploy_path="${DEPLOY_DIR}/${artifact_name}"
  local mvn_cmd=(
    mvn clean package
    -pl "${module_path}"
    -am
    -DskipTests
  )

  print_execution_plan \
    "${resolved_service}" \
    "${module_path}" \
    "${artifact_path}" \
    "${deploy_path}" \
    "${mvn_cmd[@]}"

  if [[ "${DRY_RUN}" == "${DRY_RUN_ENABLED}" ]]; then
    exit 0
  fi

  run_deploy "${artifact_path}" "${deploy_path}" "${mvn_cmd[@]}"
}

main "$@"
