#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_ROOT/../../.." && pwd)"
DEFAULT_MATRIX="$SKILL_ROOT/contracts/service-capability-matrix.yaml"
DEFAULT_TASK_SPEC="$SKILL_ROOT/contracts/test-task-spec.yaml"
RESOLVE_SCRIPT="$SCRIPT_DIR/resolve-launch-plan.py"

SERVICE=""
MATRIX_PATH="$DEFAULT_MATRIX"
TASK_SPEC_PATH="$DEFAULT_TASK_SPEC"
TASK_ID=""
ENDPOINT=""
METHOD=""
MANUAL_CONFIRMED=0
JSON_OUTPUT=0

usage() {
  cat <<'EOF'
用法:
  run-preflight.sh --service <service-name> --task-id <task-id> [--endpoint <path> --method <HTTP_METHOD>] [--matrix <path>] [--task-spec <path>] [--manual-confirmed] [--json]
  run-preflight.sh --service <service-name> --endpoint <path> --method <HTTP_METHOD> [--matrix <path>] [--task-spec <path>] [--manual-confirmed] [--json]

说明:
  1. 先校验契约文件本身是否存在且结构完整
  2. 再校验基础命令是否可用
  3. 模板任务模式会校验 task-id 对应实例
  4. 直接接口模式会尝试自动匹配控制器家族模板
  5. 最后按 service-capability-matrix 对目标服务做阻塞判断
EOF
}

while (($# > 0)); do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --service)
      SERVICE="${2:-}"
      shift 2
      ;;
    --matrix)
      MATRIX_PATH="${2:-}"
      shift 2
      ;;
    --task-spec)
      TASK_SPEC_PATH="${2:-}"
      shift 2
      ;;
    --task-id)
      TASK_ID="${2:-}"
      shift 2
      ;;
    --endpoint)
      ENDPOINT="${2:-}"
      shift 2
      ;;
    --method)
      METHOD="${2:-}"
      shift 2
      ;;
    --manual-confirmed)
      MANUAL_CONFIRMED=1
      shift
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$SERVICE" ]]; then
  echo "--service 必填，预检需要按目标服务做阻塞判断" >&2
  exit 2
fi

if [[ -z "$TASK_ID" && -z "$ENDPOINT" ]]; then
  echo "必须提供 --task-id 或 --endpoint" >&2
  exit 2
fi

if [[ -n "$ENDPOINT" && -z "$METHOD" ]]; then
  echo "指定 --endpoint 时必须同时提供 --method" >&2
  exit 2
fi

for cmd in python3 curl rg ss redis-cli; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "缺少基础命令: $cmd" >&2
    exit 3
  fi
done

if [[ ! -f "$RESOLVE_SCRIPT" ]]; then
  echo "未找到 resolve-launch-plan.py: $RESOLVE_SCRIPT" >&2
  exit 3
fi

MATRIX_PATH_ABS="$MATRIX_PATH"
TASK_SPEC_PATH_ABS="$TASK_SPEC_PATH"
if [[ "$MATRIX_PATH_ABS" != /* ]]; then
  MATRIX_PATH_ABS="$REPO_ROOT/$MATRIX_PATH_ABS"
fi
if [[ "$TASK_SPEC_PATH_ABS" != /* ]]; then
  TASK_SPEC_PATH_ABS="$REPO_ROOT/$TASK_SPEC_PATH_ABS"
fi

VALIDATION_META="$(python3 - "$SERVICE" "$TASK_ID" "$ENDPOINT" "$METHOD" "$MATRIX_PATH_ABS" "$TASK_SPEC_PATH_ABS" <<'PY'
import json
import sys
from pathlib import Path

import yaml

service = sys.argv[1]
task_id = sys.argv[2]
endpoint = sys.argv[3]
method = sys.argv[4]
matrix_path = Path(sys.argv[5])
task_spec_path = Path(sys.argv[6])

required_service_fields = {
    "service_name",
    "module_path",
    "launch_sources",
    "prelaunch_actions",
    "default_dependencies",
    "token_requirement",
    "redis_db_rule",
    "db_scopes",
    "evidence_status",
    "cleanup_rule",
    "notes",
}
required_task_fields = {
    "target_service",
    "target_endpoint",
    "request_method",
    "request_payload_or_file_spec",
    "expected_http_signal",
    "expected_log_markers",
    "expected_redis_checks",
    "expected_db_checks",
    "expected_downstream_evidence",
    "cleanup_targets",
}


def normalize_db_checks_spec(raw, resolved_endpoint=None):
    if isinstance(raw, list):
        return {"mode": "required", "checks": raw}
    if not isinstance(raw, dict):
        return None

    mode = raw.get("mode", "required")
    if mode == "skip":
        return {"mode": "skip", "checks": []}
    if mode == "required":
        return {"mode": "required", "checks": raw.get("checks") or []}
    if mode != "per_endpoint":
        fail(f"expected_db_checks.mode 非法: {mode}")

    rules = raw.get("endpoint_rules") or []
    if resolved_endpoint:
        for rule in rules:
            if rule.get("endpoint") != resolved_endpoint:
                continue
            rule_mode = rule.get("mode", "required")
            if rule_mode == "skip":
                return {"mode": "skip", "checks": []}
            if rule_mode != "required":
                fail(f"expected_db_checks.endpoint_rules[{resolved_endpoint}] 的 mode 非法: {rule_mode}")
            return {"mode": "required", "checks": rule.get("checks") or []}

    default_spec = raw.get("default", "skip")
    if isinstance(default_spec, dict):
        default_mode = default_spec.get("mode", "skip")
        default_checks = default_spec.get("checks") or []
    else:
        default_mode = default_spec
        default_checks = []

    if default_mode == "skip":
        return {"mode": "skip", "checks": []}
    if default_mode != "required":
        fail(f"expected_db_checks.default 非法: {default_mode}")
    return {"mode": "required", "checks": default_checks}


def fail(message: str, code: int = 4) -> None:
    sys.stderr.write(message + "\n")
    raise SystemExit(code)


if not matrix_path.is_file():
    fail(f"缺少服务能力矩阵: {matrix_path}")
if not task_spec_path.is_file():
    fail(f"缺少任务输入契约: {task_spec_path}")

with matrix_path.open("r", encoding="utf-8") as handle:
    matrix_data = yaml.safe_load(handle) or {}
with task_spec_path.open("r", encoding="utf-8") as handle:
    task_spec = yaml.safe_load(handle) or {}

matrix_required_fields = matrix_data.get("required_fields")
if not isinstance(matrix_required_fields, list):
    fail("service-capability-matrix 缺少 required_fields 列表")
missing_matrix_contract_fields = [field for field in required_service_fields if field not in matrix_required_fields]
if missing_matrix_contract_fields:
    fail("service-capability-matrix.required_fields 缺少字段: " + ", ".join(missing_matrix_contract_fields))

if isinstance(matrix_data, dict) and isinstance(matrix_data.get("services"), list):
    services = matrix_data["services"]
elif isinstance(matrix_data, list):
    services = matrix_data
elif isinstance(matrix_data, dict) and all(isinstance(value, dict) for value in matrix_data.values()):
    services = []
    for name, value in matrix_data.items():
        item = dict(value)
        item.setdefault("service_name", name)
        services.append(item)
else:
    fail("service-capability-matrix 结构非法，必须能解析出 services 列表")

target_service = None
for item in services:
    if item.get("service_name") == service:
        target_service = item
        break
if target_service is None:
    fail(f"服务能力矩阵中不存在服务: {service}")

missing_service = [field for field in required_service_fields if target_service.get(field) in (None, "")]
if missing_service:
    fail(f"服务 {service} 缺少必填字段: {', '.join(missing_service)}")

for list_field in ("launch_sources", "prelaunch_actions", "db_scopes"):
    value = target_service.get(list_field)
    if value in (None, ""):
        fail(f"服务 {service} 的 {list_field} 不能为空")
    if isinstance(value, list) and not value:
        fail(f"服务 {service} 的 {list_field} 不能为空列表")

task_required_fields = task_spec.get("required_fields")
if not isinstance(task_required_fields, list):
    fail("test-task-spec 缺少 required_fields 列表")
missing_task_contract_fields = [field for field in required_task_fields if field not in task_required_fields]
if missing_task_contract_fields:
    fail("test-task-spec.required_fields 缺少字段: " + ", ".join(missing_task_contract_fields))

allowed_values = task_spec.get("allowed_values") or {}
allowed_target_services = allowed_values.get("target_service") or []
if service not in allowed_target_services:
    fail(f"test-task-spec.allowed_values.target_service 未覆盖服务: {service}")

allowed_methods = set(allowed_values.get("request_method") or [])
placeholder_values = task_spec.get("placeholder_values_blocked")
if not isinstance(placeholder_values, list) or not placeholder_values:
    fail("test-task-spec 缺少 placeholder_values_blocked 列表")


def contains_placeholder(value):
    if isinstance(value, str):
        stripped = value.strip()
        return stripped in placeholder_values or stripped in {"同上", "按默认", "空"}
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    return False


meta = {
    "resolved_task_mode": "template_task" if task_id else "ad_hoc_endpoint",
    "resolved_task_id": task_id or None,
    "resolved_endpoint": endpoint or None,
    "resolved_method": method or None,
    "matched_template_task_id": None,
    "matched_template_match_mode": None,
}

example_tasks = task_spec.get("example_tasks") or []

if task_id:
    if not isinstance(example_tasks, list) or not example_tasks:
        fail("模板任务模式下，test-task-spec 缺少 example_tasks 列表")

    task = None
    for item in example_tasks:
        if item.get("task_id") == task_id:
            task = item
            break
    if task is None:
        fail(f"test-task-spec 中不存在 task_id={task_id} 的任务实例")

    missing_task_fields = []
    for field in required_task_fields:
        value = task.get(field)
        if value is None or value == "":
            missing_task_fields.append(field)
            continue
        if isinstance(value, list) and not value and field in {
            "expected_log_markers",
            "expected_downstream_evidence",
        }:
            missing_task_fields.append(field)
    if missing_task_fields:
        fail(f"任务 {task_id} 缺少必填字段: {', '.join(missing_task_fields)}")

    if contains_placeholder(task):
        fail(f"任务 {task_id} 仍包含占位值或不确定值")

    if task.get("target_service") != service:
        fail(f"任务 {task_id} 的 target_service={task.get('target_service')} 与目标服务 {service} 不一致")

    target_endpoint = task.get("target_endpoint") or {}
    match_mode = target_endpoint.get("match_mode", "exact")
    task_path = target_endpoint.get("path")
    task_method = task.get("request_method")
    meta["matched_template_task_id"] = task_id
    meta["matched_template_match_mode"] = match_mode

    if match_mode == "prefix":
        if not endpoint:
            fail(f"任务 {task_id} 是控制器家族模板，必须同时提供 --endpoint")
        if not endpoint.startswith(task_path.rstrip("/") + "/"):
            fail(f"任务 {task_id} 的接口前缀={task_path}，无法匹配目标接口 {endpoint}")
        if method != task_method:
            fail(f"任务 {task_id} 的请求方式={task_method}，与目标接口方式 {method} 不一致")
    else:
        resolved_endpoint = endpoint or task_path
        if resolved_endpoint != task_path:
            fail(f"任务 {task_id} 绑定的是精确接口 {task_path}，不能改成 {resolved_endpoint}")
        endpoint = resolved_endpoint
        method = task_method

    db_checks_spec = normalize_db_checks_spec(task.get("expected_db_checks"), endpoint)
    if db_checks_spec is None:
        fail(f"任务 {task_id} 的 expected_db_checks 结构非法")
    if db_checks_spec["mode"] == "required" and not db_checks_spec["checks"]:
        fail(f"任务 {task_id} 的 expected_db_checks 要求查库，但未声明检查项")

    service_scopes = target_service.get("db_scopes") or []
    for db_check in db_checks_spec["checks"]:
        db_scope = db_check.get("db_scope")
        if db_scope not in service_scopes:
            fail(f"任务 {task_id} 的 db_scope={db_scope} 不在服务 {service} 的允许范围内")

    expected_http_signal = task.get("expected_http_signal")
    if not isinstance(expected_http_signal, dict) or not expected_http_signal:
        fail(f"任务 {task_id} 缺少 expected_http_signal 内容")

    expected_log_markers = task.get("expected_log_markers")
    if not isinstance(expected_log_markers, dict) or not expected_log_markers.get("markers"):
        fail(f"任务 {task_id} 缺少 expected_log_markers.markers")

    cleanup_targets = task.get("cleanup_targets")
    if not isinstance(cleanup_targets, dict):
        fail(f"任务 {task_id} 的 cleanup_targets 必须是对象")

    meta["resolved_endpoint"] = endpoint
    meta["resolved_method"] = method
else:
    if not endpoint.startswith("/"):
        fail(f"直接接口模式下接口路径必须以 / 开头: {endpoint}")
    if method not in allowed_methods:
        fail(f"直接接口模式下请求方式非法: {method}")

    exact_matches = []
    prefix_matches = []
    for item in example_tasks:
        if item.get("target_service") != service:
            continue
        target_endpoint = item.get("target_endpoint") or {}
        candidate_path = target_endpoint.get("path")
        candidate_method = item.get("request_method")
        match_mode = target_endpoint.get("match_mode", "exact")
        if not candidate_path or candidate_method != method:
            continue
        if match_mode == "exact" and endpoint == candidate_path:
            exact_matches.append((len(candidate_path), item.get("task_id"), match_mode))
        if match_mode == "prefix" and endpoint.startswith(candidate_path.rstrip("/") + "/"):
            prefix_matches.append((len(candidate_path), item.get("task_id"), match_mode))

    if exact_matches:
        exact_matches.sort(reverse=True)
        _, meta["matched_template_task_id"], meta["matched_template_match_mode"] = exact_matches[0]
    elif prefix_matches:
        prefix_matches.sort(reverse=True)
        _, meta["matched_template_task_id"], meta["matched_template_match_mode"] = prefix_matches[0]

print(json.dumps(meta, ensure_ascii=False))
PY
)"

resolve_args=(python3 "$RESOLVE_SCRIPT" --service "$SERVICE" --matrix "$MATRIX_PATH_ABS")
if ((MANUAL_CONFIRMED)); then
  resolve_args+=(--manual-confirmed)
fi
if ((JSON_OUTPUT)); then
  resolve_args+=(--json)
fi
RESULT="$("${resolve_args[@]}")"
if ((JSON_OUTPUT)); then
  python3 - "$VALIDATION_META" "$RESULT" <<'PY'
import json
import sys

meta = json.loads(sys.argv[1])
plan = json.loads(sys.argv[2])
plan["task_mode"] = meta["resolved_task_mode"]
if meta["resolved_task_id"]:
    plan["task_id"] = meta["resolved_task_id"]
if meta["resolved_endpoint"]:
    plan["target_endpoint"] = meta["resolved_endpoint"]
if meta["resolved_method"]:
    plan["request_method"] = meta["resolved_method"]
if meta["matched_template_task_id"]:
    plan["matched_template_task_id"] = meta["matched_template_task_id"]
    plan["matched_template_match_mode"] = meta["matched_template_match_mode"]
print(json.dumps(plan, ensure_ascii=False, indent=2))
PY
else
  printf '%s\n' "$RESULT"
  python3 - "$VALIDATION_META" <<'PY'
import json
import sys

meta = json.loads(sys.argv[1])
print(f"task_mode: {meta['resolved_task_mode']}")
if meta["resolved_task_id"]:
    print(f"task_id: {meta['resolved_task_id']}")
if meta["resolved_endpoint"]:
    print(f"target_endpoint: {meta['resolved_endpoint']}")
if meta["resolved_method"]:
    print(f"request_method: {meta['resolved_method']}")
if meta["matched_template_task_id"]:
    print(f"matched_template_task_id: {meta['matched_template_task_id']}")
    print(f"matched_template_match_mode: {meta['matched_template_match_mode']}")
PY
fi
