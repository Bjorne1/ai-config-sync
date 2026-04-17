#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

import yaml


ALLOWED_SERVICES = {
    "ai-service",
    "drg-service",
    "emr-service",
    "his-service",
    "interface-service",
    "pay-service",
    "report-service",
}
ALLOWED_PRELAUNCH_ACTIONS = {"none", "prepare-drg-wsl-config", "manual_confirmation_required"}
ALLOWED_TOKEN_REQUIREMENTS = {"required", "not_required", "conditional"}
ALLOWED_REDIS_DB_RULES = {"from_profile_config", "from_runtime_file", "not_applicable", "unknown"}
ALLOWED_DB_SCOPES = {"his", "wh_ai", "wh_drg", "wh_pay", "wh_report", "wh_system"}
ALLOWED_EVIDENCE_STATUS = {"READY", "REQUIRES_MANUAL_CONFIRMATION", "BLOCKED"}
ALLOWED_CLEANUP_RULES = {"redis_only_expire", "non_redis_cleanup_required", "no_cleanup", "unknown"}
REQUIRED_FIELDS = {
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

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parent.parent
REPO_ROOT = SCRIPT_PATH.parents[4]
DEFAULT_MATRIX_PATH = SKILL_ROOT / "contracts" / "service-capability-matrix.yaml"
PROFILE_PATTERN = re.compile(r"-Dspring\.profiles\.active=([^\s]+)")
ADDITIONAL_LOCATION_PATTERN = re.compile(r"-Dspring\.config\.additional-location=file:([^\s]+)")


def parse_args():
    parser = argparse.ArgumentParser(description="根据 service-capability-matrix 解析服务启动计划")
    parser.add_argument("--service", required=True, help="目标服务名")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX_PATH), help="service-capability-matrix.yaml 路径")
    parser.add_argument("--manual-confirmed", action="store_true", help="已人工确认可继续执行")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def fail(message, code=1):
    sys.stderr.write(f"{message}\n")
    raise SystemExit(code)


def resolve_repo_path(path_text):
    path = Path(str(path_text)).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_yaml(path_text, label):
    path = resolve_repo_path(path_text)
    if not path.is_file():
        fail(f"未找到 {label}: {path}", 2)
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


def normalize_string_list(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []


def iter_launch_source_dicts(launch_sources):
    for item in normalize_string_list(launch_sources):
        if isinstance(item, dict):
            yield item


def iter_launch_source_paths(launch_sources, source_type=None):
    for item in normalize_string_list(launch_sources):
        if isinstance(item, str):
            if source_type in (None, "path"):
                yield item, None
            continue
        if not isinstance(item, dict):
            continue
        if source_type is not None and item.get("type") != source_type:
            continue
        path = item.get("path") or item.get("file")
        if path:
            yield path, item


def validate_service_entry(entry):
    missing = [field for field in REQUIRED_FIELDS if field not in entry or entry.get(field) in (None, "")]
    if missing:
        fail(f"服务 {entry.get('service_name', '<unknown>')} 缺少必填字段: {', '.join(missing)}", 3)

    service_name = entry["service_name"]
    if service_name not in ALLOWED_SERVICES:
        fail(f"非法服务名: {service_name}", 3)

    launch_sources = normalize_string_list(entry["launch_sources"])
    if not launch_sources:
        fail(f"服务 {service_name} 的 launch_sources 不能为空", 3)

    prelaunch_actions = normalize_string_list(entry["prelaunch_actions"])
    if not prelaunch_actions:
        fail(f"服务 {service_name} 的 prelaunch_actions 不能为空", 3)
    invalid_actions = [item for item in prelaunch_actions if item not in ALLOWED_PRELAUNCH_ACTIONS]
    if invalid_actions:
        fail(f"服务 {service_name} 的 prelaunch_actions 非法: {', '.join(invalid_actions)}", 3)

    token_requirement = entry["token_requirement"]
    if token_requirement not in ALLOWED_TOKEN_REQUIREMENTS:
        fail(f"服务 {service_name} 的 token_requirement 非法: {token_requirement}", 3)

    redis_db_rule = entry["redis_db_rule"]
    redis_db_rule_type = redis_db_rule.get("type") if isinstance(redis_db_rule, dict) else redis_db_rule
    if redis_db_rule_type not in ALLOWED_REDIS_DB_RULES:
        fail(f"服务 {service_name} 的 redis_db_rule 非法: {redis_db_rule_type}", 3)

    db_scopes = normalize_string_list(entry["db_scopes"])
    if not db_scopes:
        fail(f"服务 {service_name} 的 db_scopes 不能为空", 3)
    invalid_scopes = [item for item in db_scopes if item not in ALLOWED_DB_SCOPES]
    if invalid_scopes:
        fail(f"服务 {service_name} 的 db_scopes 非法: {', '.join(invalid_scopes)}", 3)

    evidence_status = entry["evidence_status"]
    if evidence_status not in ALLOWED_EVIDENCE_STATUS:
        fail(f"服务 {service_name} 的 evidence_status 非法: {evidence_status}", 3)

    cleanup_rule = entry["cleanup_rule"]
    if cleanup_rule not in ALLOWED_CLEANUP_RULES:
        fail(f"服务 {service_name} 的 cleanup_rule 非法: {cleanup_rule}", 3)

    if evidence_status == "READY":
        if redis_db_rule_type == "unknown" or cleanup_rule == "unknown":
            fail(f"服务 {service_name} 标记为 READY，但仍包含 unknown 字段", 3)


def load_matrix_service(matrix_path, service_name):
    _, matrix_data = load_yaml(matrix_path, "service-capability-matrix")
    services = normalize_services(matrix_data)
    if not services:
        fail("service-capability-matrix 中未找到 services", 3)
    for entry in services:
        validate_service_entry(entry)
        if entry.get("service_name") == service_name:
            return entry
    fail(f"service-capability-matrix 中不存在服务: {service_name}", 3)


def parse_launch_json(path):
    launch_path, data = load_yaml(path, "launch.json")
    configs = data.get("configurations")
    if not isinstance(configs, list):
        fail(f"launch.json 缺少 configurations: {launch_path}", 3)
    return launch_path, configs


def parse_tasks_json(path):
    tasks_path, data = load_yaml(path, "tasks.json")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return tasks_path, []
    return tasks_path, tasks


def match_launch_config(service_name, launch_sources):
    launch_candidates = list(iter_launch_source_paths(launch_sources, "vscode_launch"))
    if not launch_candidates:
        launch_candidates = [
            (path, meta)
            for path, meta in iter_launch_source_paths(launch_sources)
            if str(path).endswith("launch.json")
        ]
    if not launch_candidates:
        return None
    launch_path_text, source_meta = launch_candidates[0]
    launch_path, configs = parse_launch_json(launch_path_text)
    locator = (source_meta or {}).get("locator")
    if locator:
        for config in configs:
            if config.get("name") == locator:
                return {"path": str(launch_path), "config": config}
        fail(f"launch.json 未找到 locator={locator} 的配置", 3)
    for config in configs:
        if config.get("projectName") == service_name:
            return {"path": str(launch_path), "config": config}
    return {"path": str(launch_path), "config": None}


def resolve_prelaunch_tasks(launch_config, launch_sources):
    task_label = (launch_config or {}).get("preLaunchTask")
    if not task_label:
        return []
    task_sources = []
    launch_source_items = normalize_string_list(launch_sources)
    task_sources.extend(path for path, _ in iter_launch_source_paths(launch_sources, "vscode_task"))
    if not task_sources:
        task_sources.extend(
            item for item in launch_source_items if isinstance(item, str) and item.endswith("tasks.json")
        )
    if not task_sources:
        task_sources.append(".vscode/tasks.json")
    tasks_path, tasks = parse_tasks_json(task_sources[0])
    matches = [task for task in tasks if task.get("label") == task_label]
    if not matches:
        fail(f"tasks.json 未找到 preLaunchTask={task_label}", 3)
    return [{"path": str(tasks_path), "task": task} for task in matches]


def extract_runtime_files(launch_config, launch_sources, module_path):
    runtime_files = []
    for item, _ in iter_launch_source_paths(launch_sources):
        if str(item).endswith((".yaml", ".yml")):
            runtime_files.append(str(resolve_repo_path(item)))
    config = launch_config or {}
    vm_args = config.get("vmArgs", "")
    for match in ADDITIONAL_LOCATION_PATTERN.finditer(vm_args):
        runtime_files.append(match.group(1).replace("${workspaceFolder}", str(REPO_ROOT)))
    module_dir = resolve_repo_path(module_path)
    if module_dir.exists():
        for fallback in (
            module_dir / "src/main/resources/bootstrap-emr.yaml",
            module_dir / "src/main/resources/bootstrap-wh.yaml",
            module_dir / "src/main/resources/bootstrap-wcs.yaml",
            module_dir / "src/main/resources/bootstrap.yaml",
        ):
            if fallback.is_file():
                runtime_files.append(str(fallback))
    ordered = []
    seen = set()
    for item in runtime_files:
        normalized = str(resolve_repo_path(item))
        if normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
    return ordered


def build_plan(entry):
    launch_sources = entry["launch_sources"]
    launch_match = match_launch_config(entry["service_name"], launch_sources)
    launch_config = (launch_match or {}).get("config")
    prelaunch_tasks = resolve_prelaunch_tasks(launch_config, launch_sources) if launch_config else []
    vm_args = launch_config.get("vmArgs", "") if launch_config else ""
    profile_match = PROFILE_PATTERN.search(vm_args)
    return {
        "service_name": entry["service_name"],
        "module_path": str(resolve_repo_path(entry["module_path"])),
        "launch_sources": launch_sources,
        "launch_config_found": bool(launch_config),
        "launch_config": launch_config,
        "launch_config_path": (launch_match or {}).get("path"),
        "prelaunch_tasks": prelaunch_tasks,
        "default_dependencies": normalize_string_list(entry["default_dependencies"]),
        "token_requirement": entry["token_requirement"],
        "redis_db_rule": entry["redis_db_rule"],
        "db_scopes": normalize_string_list(entry["db_scopes"]),
        "evidence_status": entry["evidence_status"],
        "manual_intervention_required": entry["evidence_status"] == "REQUIRES_MANUAL_CONFIRMATION",
        "cleanup_rule": entry["cleanup_rule"],
        "notes": entry["notes"],
        "profile": profile_match.group(1) if profile_match else None,
        "runtime_files": extract_runtime_files(launch_config, launch_sources, entry["module_path"]),
    }


def emit(plan, as_json):
    if as_json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    print(f"service_name: {plan['service_name']}")
    print(f"evidence_status: {plan['evidence_status']}")
    print(f"module_path: {plan['module_path']}")
    print(f"default_dependencies: {', '.join(plan['default_dependencies']) or '(none)'}")
    print(f"token_requirement: {plan['token_requirement']}")
    print(f"profile: {plan['profile'] or '(unknown)'}")
    if plan["launch_config_found"]:
        print(f"launch_config_path: {plan['launch_config_path']}")
    else:
        print("launch_config_path: (not found)")
    if plan["runtime_files"]:
        print("runtime_files:")
        for item in plan["runtime_files"]:
            print(f"  - {item}")


def main():
    args = parse_args()
    entry = load_matrix_service(args.matrix, args.service)
    evidence_status = entry["evidence_status"]
    if evidence_status == "BLOCKED":
        fail(f"服务 {args.service} 在矩阵中标记为 BLOCKED，禁止继续执行", 4)
    if evidence_status == "REQUIRES_MANUAL_CONFIRMATION" and not args.manual_confirmed:
        fail(
            f"服务 {args.service} 在矩阵中标记为 REQUIRES_MANUAL_CONFIRMATION，请先人工确认后重试并追加 --manual-confirmed",
            5,
        )
    plan = build_plan(entry)
    plan["manual_intervention_confirmed"] = bool(args.manual_confirmed)
    emit(plan, args.json)


if __name__ == "__main__":
    main()
