from pathlib import Path

from .file_sync import has_path
from .tool_definitions import ENVIRONMENT_IDS, GLOBAL_RULE_FILE_NAMES, GLOBAL_RULE_TOOL_IDS


def build_global_rule_target_path(root_path: str | None, tool_id: str) -> str | None:
    if not root_path:
        return None
    return str(Path(root_path) / GLOBAL_RULE_FILE_NAMES[tool_id])


def build_global_rule_statuses(
    global_rules: dict[str, object],
    environment_list: dict[str, object],
) -> list[dict[str, object]]:
    profiles = global_rules.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("global_rules.profiles 必须是数组。")
    assignments = global_rules.get("assignments")
    if not isinstance(assignments, dict):
        raise ValueError("global_rules.assignments 必须是 object。")
    profile_index = {
        str(profile["id"]): profile
        for profile in profiles
        if isinstance(profile, dict) and profile.get("id")
    }
    statuses: list[dict[str, object]] = []
    for environment_id in ENVIRONMENT_IDS:
        environment = environment_list[environment_id]
        environment_assignments = assignments.get(environment_id, {})
        for tool_id in GLOBAL_RULE_TOOL_IDS:
            profile_id = environment_assignments.get(tool_id)
            profile = profile_index.get(str(profile_id)) if profile_id else None
            root_path = environment["roots"].get(tool_id)
            target_path = build_global_rule_target_path(root_path, tool_id)
            state = "idle"
            message = "未分配规则版本"
            if environment["id"] == "wsl" and environment.get("error"):
                state = "environment_error"
                message = str(environment["error"])
            elif not root_path:
                state = "tool_unavailable"
                message = "工具目录不存在"
            elif profile_id and profile is None:
                state = "profile_missing"
                message = f"规则版本不存在：{profile_id}"
            elif profile:
                if not target_path or not has_path(target_path):
                    state = "outdated"
                    message = "目标文件缺失，等待同步"
                else:
                    try:
                        target_content = Path(target_path).read_text(encoding="utf-8")
                    except OSError as error:
                        state = "drifted"
                        message = f"读取目标文件失败：{error}"
                    else:
                        if target_content == profile.get("content", ""):
                            state = "healthy"
                            message = "已同步"
                        else:
                            state = "drifted"
                            message = "目标文件内容与规则版本不一致"
            statuses.append(
                {
                    "environmentId": environment_id,
                    "toolId": tool_id,
                    "targetFilePath": target_path,
                    "profileId": profile_id,
                    "profileName": profile.get("name") if profile else None,
                    "state": state,
                    "message": message,
                }
            )
    return statuses
