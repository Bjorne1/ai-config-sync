from pathlib import Path

from .global_rule_runtime_service import build_global_rule_statuses
from .tool_definitions import ENVIRONMENT_IDS, GLOBAL_RULE_TOOL_IDS


def _normalize_targets(targets: list[dict[str, str]] | None) -> list[tuple[str, str]] | None:
    if targets is None:
        return None
    normalized: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in targets:
        if not isinstance(item, dict):
            raise ValueError("sync targets 必须是对象数组。")
        environment_id = str(item.get("environmentId") or "").strip()
        tool_id = str(item.get("toolId") or "").strip()
        if environment_id not in ENVIRONMENT_IDS:
            raise ValueError(f"不支持的 environmentId：{environment_id}")
        if tool_id not in GLOBAL_RULE_TOOL_IDS:
            raise ValueError(f"不支持的 toolId：{tool_id}")
        key = (environment_id, tool_id)
        if key in seen:
            continue
        normalized.append(key)
        seen.add(key)
    return normalized


def sync_global_rules(
    global_rules: dict[str, object],
    environment_list: dict[str, object],
    targets: list[dict[str, str]] | None = None,
) -> list[dict[str, object]]:
    statuses = build_global_rule_statuses(global_rules, environment_list)
    status_index = {
        (item["environmentId"], item["toolId"]): item
        for item in statuses
    }
    normalized_targets = _normalize_targets(targets)
    profile_index = {
        str(profile["id"]): profile
        for profile in global_rules.get("profiles", [])
        if isinstance(profile, dict) and profile.get("id")
    }
    if normalized_targets is None:
        normalized_targets = [
            (item["environmentId"], item["toolId"])
            for item in statuses
            if item.get("profileId")
        ]
    results: list[dict[str, object]] = []
    for environment_id, tool_id in normalized_targets:
        status = status_index[(environment_id, tool_id)]
        profile_id = status.get("profileId")
        profile = profile_index.get(str(profile_id)) if profile_id else None
        target_path = status.get("targetFilePath")
        result = {
            "environmentId": environment_id,
            "toolId": tool_id,
            "targetFilePath": target_path,
            "profileId": profile_id,
            "profileName": status.get("profileName"),
            "success": False,
            "skipped": False,
        }
        if not profile:
            results.append({**result, "skipped": True, "message": "未分配规则版本"})
            continue
        if status["state"] in {"environment_error", "tool_unavailable", "profile_missing"}:
            results.append({**result, "message": status["message"]})
            continue
        if not target_path:
            results.append({**result, "message": "目标文件路径不可用"})
            continue
        try:
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            Path(target_path).write_text(str(profile.get("content") or ""), encoding="utf-8")
        except OSError as error:
            results.append({**result, "message": str(error)})
            continue
        results.append({**result, "success": True, "message": "同步成功"})
    return results
