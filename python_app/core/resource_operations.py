from copy import deepcopy
from pathlib import Path

from . import file_sync
from .resource_service import (
    expand_resource_items,
    get_configured_resources,
    get_resource_catalog,
    get_resource_entry,
    list_managed_names,
)
from .runtime_service import build_availability
from .sync_engine import describe_target_state, remove_target, sync_entry
from .tool_definitions import TOOL_IDS


def aggregate_states(states: list[dict[str, object]]) -> dict[str, str]:
    kinds = [state["state"] for state in states]
    if not states:
        return {"state": "missing", "message": "未发现可同步项"}
    if "conflict" in kinds:
        return {"state": "conflict", "message": "部分目标存在冲突"}
    if "source_missing" in kinds:
        return {"state": "source_missing", "message": "源文件不存在"}
    if "tool_unavailable" in kinds:
        return {"state": "tool_unavailable", "message": "工具目录不存在"}
    if "environment_error" in kinds:
        return {"state": "environment_error", "message": "环境不可用"}
    if all(kind == "healthy" for kind in kinds):
        return {"state": "healthy", "message": "已同步"}
    if all(kind == "missing" for kind in kinds):
        return {"state": "missing", "message": "目标缺失"}
    return {"state": "partial", "message": "部分目标已同步"}


def _build_target_paths(base_target: str | None, items: list[dict[str, object]]) -> list[str]:
    if not base_target:
        return []
    return [str(Path(base_target) / item["name"]) for item in items]


def _build_states_for_targets(
    mode: str,
    items: list[dict[str, object]],
    target_paths: list[str],
    availability: dict[str, object],
) -> list[dict[str, object]]:
    if not availability["available"]:
        if not target_paths:
            return [{"state": availability["state"], "message": availability["message"], "targetPath": None}]
        return [
            {
                "state": availability["state"],
                "message": availability["message"],
                "targetPath": target_path,
            }
            for target_path in target_paths
        ]
    return [
        {
            **describe_target_state(mode, item["sourcePath"], target_paths[index]),
            "targetPath": target_paths[index],
        }
        for index, item in enumerate(items)
    ]


def _iter_enabled_environments(environment_list: dict[str, object]) -> list[dict[str, object]]:
    return list(environment_list.values())


def _build_entries_for_resource(
    config: dict[str, object],
    kind: str,
    resource: dict[str, object],
    configured_targets: dict[str, list[str]],
    environment_list: dict[str, object],
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for environment in _iter_enabled_environments(environment_list):
        environment_tools = configured_targets.get(environment["id"], [])
        for tool_id in TOOL_IDS:
            if tool_id not in environment_tools:
                continue
            items = expand_resource_items(config, kind, resource, tool_id)
            availability = build_availability(environment, kind, tool_id)
            base_target = environment["targets"][kind][tool_id]
            target_paths = _build_target_paths(base_target, items)
            states = _build_states_for_targets(config["syncMode"], items, target_paths, availability)
            summary = aggregate_states(states)
            entries.append(
                {
                    "environmentId": environment["id"],
                    "toolId": tool_id,
                    "state": summary["state"],
                    "message": summary["message"],
                    "itemCount": len(items),
                    "targetPath": base_target,
                    "targets": target_paths,
                }
            )
    return entries


def detect_existing_targets(
    config: dict[str, object],
    kind: str,
    resource: dict[str, object],
    environment_list: dict[str, object],
) -> dict[str, list[str]]:
    detected: dict[str, list[str]] = {}
    for environment in _iter_enabled_environments(environment_list):
        tools: list[str] = []
        for tool_id in TOOL_IDS:
            availability = build_availability(environment, kind, tool_id)
            if not availability["available"]:
                continue
            items = expand_resource_items(config, kind, resource, tool_id)
            target_paths = _build_target_paths(environment["targets"][kind][tool_id], items)
            if any(file_sync.has_path(target_path) for target_path in target_paths):
                tools.append(tool_id)
        if tools:
            detected[environment["id"]] = tools
    return detected


def merge_environment_targets(*target_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for environment_id in ("windows", "wsl"):
        ordered = [
            tool_id
            for tool_id in TOOL_IDS
            if any(tool_id in targets.get(environment_id, []) for targets in target_sets)
        ]
        if ordered:
            merged[environment_id] = ordered
    return merged


def build_resource_statuses(
    config: dict[str, object],
    kind: str,
    environment_list: dict[str, object],
) -> list[dict[str, object]]:
    catalog = get_resource_catalog(config)
    index = catalog["skillIndex"] if kind == "skills" else catalog["commandIndex"]
    statuses: list[dict[str, object]] = []
    for name in list_managed_names(config, kind, index):
        resource = get_resource_entry(config, kind, name, index)
        configured_targets = get_configured_resources(config, kind).get(name, {})
        statuses.append(
            {
                "kind": kind,
                "name": name,
                "sourcePath": resource["path"],
                "isDirectory": resource["isDirectory"],
                "configuredTargets": configured_targets,
                "entries": _build_entries_for_resource(
                    config,
                    kind,
                    resource,
                    configured_targets,
                    environment_list,
                ),
            }
        )
    return statuses


def sync_configured_resources(
    config: dict[str, object],
    kind: str,
    environment_list: dict[str, object],
    requested_names: list[str] | None = None,
    configured_override: dict[str, dict[str, list[str]]] | None = None,
) -> list[dict[str, object]]:
    catalog = get_resource_catalog(config)
    index = catalog["skillIndex"] if kind == "skills" else catalog["commandIndex"]
    configured = configured_override if configured_override is not None else get_configured_resources(config, kind)
    names = requested_names if requested_names is not None else list(configured.keys())
    sync_details: list[dict[str, object]] = []
    for name in names:
        resource = get_resource_entry(config, kind, name, index)
        configured_targets = configured.get(name, {})
        for environment in _iter_enabled_environments(environment_list):
            for tool_id in configured_targets.get(environment["id"], []):
                items = expand_resource_items(config, kind, resource, tool_id)
                availability = build_availability(environment, kind, tool_id)
                if not availability["available"]:
                    sync_details.append(
                        {
                            "kind": kind,
                            "name": name,
                            "toolId": tool_id,
                            "environmentId": environment["id"],
                            "success": False,
                            "skipped": True,
                            "message": availability["message"],
                        }
                    )
                    continue
                for item in items:
                    target_path = str(Path(environment["targets"][kind][tool_id]) / item["name"])
                    result = sync_entry(
                        config["syncMode"],
                        item["sourcePath"],
                        target_path,
                        item["isDirectory"],
                    )
                    sync_details.append(
                        {
                            "kind": kind,
                            "name": name,
                            "toolId": tool_id,
                            "environmentId": environment["id"],
                            "targetPath": target_path,
                            **result,
                        }
                    )
    return sync_details


def _get_cleanup_targets(kind: str, resource_name: str, entry: dict[str, object]) -> list[str]:
    if entry["targets"] and kind != "commands":
        return entry["targets"]
    if not entry["targetPath"]:
        return entry["targets"]
    if kind != "commands":
        return [str(Path(entry["targetPath"]) / resource_name)]
    direct_path = str(Path(entry["targetPath"]) / resource_name)
    flattened: list[str] = []
    target_dir = Path(entry["targetPath"])
    if target_dir.exists():
        flattened = [
            str(target_dir / item.name)
            for item in target_dir.iterdir()
            if item.name.startswith(f"{resource_name}-")
        ]
    return list(dict.fromkeys([*entry["targets"], direct_path, *flattened]))


def cleanup_invalid_resources(
    config: dict[str, object],
    environment_list: dict[str, object],
    save_config,
) -> dict[str, object]:
    next_config = deepcopy(config)
    cleaned: list[dict[str, object]] = []
    for kind in ("skills", "commands"):
        for resource in build_resource_statuses(config, kind, environment_list):
            has_missing_source = any(
                entry["state"] == "source_missing" for entry in resource["entries"]
            )
            if has_missing_source:
                next_config["resources"][kind].pop(resource["name"], None)
            for entry in resource["entries"]:
                if entry["state"] not in {"conflict", "missing", "source_missing"}:
                    continue
                for target_path in _get_cleanup_targets(resource["kind"], resource["name"], entry):
                    result = remove_target(target_path)
                    cleaned.append(
                        {
                            **entry,
                            **result,
                            "kind": kind,
                            "name": resource["name"],
                            "targetPath": target_path,
                        }
                    )
    return {"cleaned": cleaned, "config": save_config(next_config)}
