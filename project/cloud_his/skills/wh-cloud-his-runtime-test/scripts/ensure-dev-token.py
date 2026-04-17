#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


DEFAULT_TOKEN = "codex-cloud-his-dev-token"
DEFAULT_USER_ID = "codex-dev-user"
DEFAULT_USER_CODE = "codex"
DEFAULT_USER_NAME = "Codex Dev"
DEFAULT_APP_ID = "1660581392648130562"
DEFAULT_LOGIN_SOFT_ID = "10001"
DEFAULT_LOGIN_OFFICE_CODE = "DEV"
DEFAULT_LOGIN_OFFICE_NAME = "开发联调科室"
DEFAULT_HOSPITAL_ID = "H0001"
DEFAULT_HOSPITAL_NAME = "开发联调医院"
DEFAULT_REDIS_HOST = "192.168.10.206"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_PASSWORD = "FJwhrj.888"
ONLINE_USER_TYPE = "com.whxx.base.domain.bo.OnlineUserModel"
ALLOWED_REDIS_RULES = {"from_profile_config", "from_runtime_file", "not_applicable", "unknown"}
REDIS_KEY_PREFIX = "TOKEN:SYS:"

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parent.parent
REPO_ROOT = SCRIPT_PATH.parents[4]
DEFAULT_MATRIX_PATH = SKILL_ROOT / "contracts" / "service-capability-matrix.yaml"
PLACEHOLDER_PATTERN = re.compile(r"^\$\{[^:}]+:(-?\d+)\}$")


def parse_args():
    parser = argparse.ArgumentParser(description="根据服务矩阵确保开发环境测试 token 已写入 Redis")
    parser.add_argument("--service", required=True, help="服务名，需存在于 service-capability-matrix")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX_PATH), help="service-capability-matrix.yaml 路径")
    parser.add_argument("--token", default=DEFAULT_TOKEN)

    parser.add_argument("--hospital-id", default=DEFAULT_HOSPITAL_ID)
    parser.add_argument("--hospital-name", default=DEFAULT_HOSPITAL_NAME)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--user-code", default=DEFAULT_USER_CODE)
    parser.add_argument("--user-name", default=DEFAULT_USER_NAME)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--login-soft-id", default=DEFAULT_LOGIN_SOFT_ID)
    parser.add_argument("--login-office-id")
    parser.add_argument("--login-office-code", default=DEFAULT_LOGIN_OFFICE_CODE)
    parser.add_argument("--login-office-name", default=DEFAULT_LOGIN_OFFICE_NAME)
    parser.add_argument("--login-ward-code")
    parser.add_argument("--login-ward-name")
    parser.add_argument("--job-title")
    parser.add_argument("--job-title-name")
    parser.add_argument("--redis-host", default=DEFAULT_REDIS_HOST)
    parser.add_argument("--redis-port", type=int, default=DEFAULT_REDIS_PORT)
    parser.add_argument("--redis-password", default=DEFAULT_REDIS_PASSWORD)
    parser.add_argument("--redis-db", type=int, help="显式指定 Redis DB；会覆盖矩阵规则解析结果")
    parser.add_argument("--ttl-seconds", type=int, default=-1, help="默认 -1，表示持久化 token")
    parser.add_argument("--dry-run", action="store_true", help="只输出解析结果，不实际写 Redis")
    parser.add_argument("--force", action="store_true", help="即使服务标记为无需 token，也继续写入")
    parser.add_argument("--manual-confirmed", action="store_true", help="服务处于人工确认态时，显式确认后继续")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    return parser.parse_args()


def fail(message, code=1):
    sys.stderr.write(f"{message}\n")
    raise SystemExit(code)


def load_yaml(path_text):
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        fail(f"未找到服务能力矩阵: {path}", 2)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return path, data


def normalize_services(raw):
    if isinstance(raw, list):
        services = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("services"), list):
            services = raw["services"]
        elif all(isinstance(value, dict) for value in raw.values()):
            services = []
            for name, value in raw.items():
                item = dict(value)
                item.setdefault("service_name", name)
                services.append(item)
        else:
            services = []
    else:
        services = []
    return services


def get_service_entry(matrix_data, service_name):
    for entry in normalize_services(matrix_data):
        if entry.get("service_name") == service_name:
            return entry
    fail(f"服务能力矩阵中不存在服务: {service_name}", 3)


def enforce_service_execution_guard(service_entry, manual_confirmed):
    service_name = service_entry.get("service_name")
    evidence_status = service_entry.get("evidence_status")
    if evidence_status == "BLOCKED":
        fail(f"服务 {service_name} 在矩阵中标记为 BLOCKED，禁止准备 token", 4)
    if evidence_status == "REQUIRES_MANUAL_CONFIRMATION" and not manual_confirmed:
        fail(
            f"服务 {service_name} 在矩阵中标记为 REQUIRES_MANUAL_CONFIRMATION，请追加 --manual-confirmed 后重试",
            5,
        )


def resolve_repo_path(candidate):
    if not candidate:
        return None
    path = Path(str(candidate)).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def extract_path_candidates(service_entry):
    candidates = []
    for key in ("runtime_file", "runtime_config", "profile_config_path", "config_path"):
        value = service_entry.get(key)
        if value:
            candidates.append(value)
    launch_sources = service_entry.get("launch_sources") or []
    if isinstance(launch_sources, str):
        launch_sources = [launch_sources]
    for source in launch_sources:
        if isinstance(source, str) and source.endswith((".yaml", ".yml")):
            candidates.append(source)
        elif isinstance(source, dict):
            for key in ("path", "file", "runtime_file", "config_path", "profile_config_path"):
                value = source.get(key)
                if value:
                    candidates.append(value)
    module_path = service_entry.get("module_path")
    service_name = service_entry.get("service_name", "")
    if module_path:
        module_dir = resolve_repo_path(module_path)
        if module_dir:
            for fallback in (
                module_dir / "src/main/resources/bootstrap-emr.yaml",
                module_dir / "src/main/resources/bootstrap-wh.yaml",
                module_dir / "src/main/resources/bootstrap-wcs.yaml",
                module_dir / "src/main/resources/bootstrap.yaml",
            ):
                candidates.append(str(fallback))
    if service_name == "drg-service":
        candidates.append(str(REPO_ROOT / ".vscode/runtime/drg-service-wcs.runtime.yaml"))
    ordered = []
    seen = set()
    for candidate in candidates:
        path = resolve_repo_path(candidate)
        if path and path not in seen:
            ordered.append(path)
            seen.add(path)
    return ordered


def parse_db_value(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        match = PLACEHOLDER_PATTERN.match(stripped)
        if match:
            return int(match.group(1))
    return None


def nested_get(data, key_path):
    current = data
    for part in key_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def resolve_redis_db_rule(service_entry):
    token_requirement = service_entry.get("token_requirement")
    if token_requirement == "not_required":
        return {"status": "skipped", "message": "服务标记为无需 token"}

    rule = service_entry.get("redis_db_rule")
    rule_type = rule.get("type") if isinstance(rule, dict) else rule
    if rule_type not in ALLOWED_REDIS_RULES:
        fail(
            f"服务 {service_entry.get('service_name')} 的 redis_db_rule 非法: {rule_type}",
            4,
        )
    if rule_type == "not_applicable":
        fail(f"服务 {service_entry.get('service_name')} 的 redis_db_rule 为 not_applicable，无法写入 token", 4)
    if rule_type == "unknown":
        fail(f"服务 {service_entry.get('service_name')} 的 redis_db_rule 为 unknown，无法判断 Redis DB", 4)

    if isinstance(rule, dict):
        for key in ("db", "database", "value", "default", "env_default"):
            parsed = parse_db_value(rule.get(key))
            if parsed is not None:
                return {"status": "resolved", "redis_db": parsed, "source": key}
        lookup_keys = [rule.get("yaml_key"), rule.get("key"), "spring.redis.database", "redis.database"]
    else:
        lookup_keys = ["spring.redis.database", "redis.database"]

    for candidate in extract_path_candidates(service_entry):
        if not candidate.is_file():
            continue
        with candidate.open("r", encoding="utf-8") as handle:
            content = yaml.safe_load(handle) or {}
        for key_path in lookup_keys:
            if not key_path:
                continue
            parsed = parse_db_value(nested_get(content, key_path))
            if parsed is not None:
                return {
                    "status": "resolved",
                    "redis_db": parsed,
                    "source": f"{candidate}:{key_path}",
                }
        if rule_type == "from_profile_config" and candidate.name.endswith(("-emr.yaml", "-emr.yml")):
            return {
                "status": "resolved",
                "redis_db": 1,
                "source": f"{candidate}:profile_default_emr",
            }

    fail(
        "未能根据服务能力矩阵解析 Redis DB；请在矩阵中补充显式值或可解析配置路径",
        5,
    )


def build_payload(args):
    payload = {
        "@type": ONLINE_USER_TYPE,
        "token": args.token,
        "loginSuccess": 1,
        "hospitalId": args.hospital_id,
        "hospitalName": args.hospital_name,
        "userId": args.user_id,
        "userCode": args.user_code,
        "userName": args.user_name,
        "appId": args.app_id,
        "loginSoftId": args.login_soft_id,
        "loginOfficeCode": args.login_office_code,
        "loginOfficeName": args.login_office_name,
    }
    if args.login_office_id:
        payload["loginOfficeId"] = args.login_office_id
    if args.login_ward_code:
        payload["loginWardCode"] = args.login_ward_code
    if args.login_ward_name:
        payload["loginWardName"] = args.login_ward_name
    if args.job_title:
        payload["jobTitle"] = args.job_title
    if args.job_title_name:
        payload["jobTitleName"] = args.job_title_name
    return payload


def redis_cli_base(args, redis_db):
    command = [
        "redis-cli",
        "-h",
        args.redis_host,
        "-p",
        str(args.redis_port),
    ]
    if args.redis_password:
        command.extend(["-a", args.redis_password])
    command.extend(["-n", str(redis_db)])
    return command


def run_redis_command(command):
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        fail(completed.stderr.strip() or completed.stdout.strip() or "redis-cli 执行失败", completed.returncode)
    return (completed.stdout or "").strip()


def apply_to_redis(args, redis_db, payload_json):
    redis_key = f"{REDIS_KEY_PREFIX}{args.token}"
    base = redis_cli_base(args, redis_db)
    if args.ttl_seconds == -1:
        run_redis_command(base + ["SET", redis_key, payload_json])
    elif args.ttl_seconds >= 0:
        run_redis_command(base + ["SETEX", redis_key, str(args.ttl_seconds), payload_json])
    else:
        fail("ttl-seconds 只能为 -1 或非负整数", 6)
    ttl_output = run_redis_command(base + ["TTL", redis_key])
    try:
        ttl_value = int(ttl_output)
    except ValueError:
        fail(f"无法解析 Redis TTL 输出: {ttl_output}", 6)
    return redis_key, ttl_value


def emit(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for key, value in result.items():
        print(f"{key}: {value}")


def main():
    args = parse_args()
    _, matrix_data = load_yaml(args.matrix)
    service_entry = get_service_entry(matrix_data, args.service)
    enforce_service_execution_guard(service_entry, args.manual_confirmed)

    # --- 写入逻辑 ---

    token_requirement = service_entry.get("token_requirement")
    if token_requirement == "not_required" and not args.force:
        emit(
            {
                "status": "skipped",
                "service": args.service,
                "manual_intervention_required": False,
                "manual_intervention_confirmed": bool(args.manual_confirmed),
                "message": "该服务在矩阵中标记为无需 token；如需强制写入，请追加 --force",
            },
            args.json,
        )
        return

    redis_resolution = (
        {"status": "resolved", "redis_db": args.redis_db, "source": "cli_override"}
        if args.redis_db is not None
        else resolve_redis_db_rule(service_entry)
    )
    if redis_resolution.get("status") != "resolved":
        fail(redis_resolution.get("message") or "Redis DB 解析失败", 7)

    payload = build_payload(args)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    redis_db = redis_resolution["redis_db"]
    result = {
        "status": "planned" if args.dry_run else "applied",
        "service": args.service,
        "evidence_status": service_entry.get("evidence_status"),
        "manual_intervention_required": service_entry.get("evidence_status") == "REQUIRES_MANUAL_CONFIRMATION",
        "manual_intervention_confirmed": bool(args.manual_confirmed),
        "redis_db": redis_db,
        "redis_db_source": redis_resolution["source"],
        "token": args.token,
        "ttl_seconds": args.ttl_seconds,
        "redis_key": f"{REDIS_KEY_PREFIX}{args.token}",
        "payload": payload,
    }
    if args.dry_run:
        emit(result, args.json)
        return

    redis_key, ttl_value = apply_to_redis(args, redis_db, payload_json)
    result["redis_key"] = redis_key
    result["redis_ttl_after_write"] = ttl_value
    emit(result, args.json)


if __name__ == "__main__":
    main()
