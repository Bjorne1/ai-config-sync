from pathlib import Path

from . import file_sync, scanner
from .environment_service import expand_posix_home_path, expand_windows_path, linux_path_to_unc
from .resource_operations import aggregate_states, merge_environment_targets
from .sync_engine import describe_target_state, remove_target, sync_entry
from .tool_definitions import ENVIRONMENT_IDS, PROJECT_SKILL_TARGET_SEGMENTS, PROJECT_SKILL_TOOL_IDS


def scan_project_skill_inventory(config: dict[str, object]) -> list[dict[str, object]]:
    projects = config.get("projectSkillProjects", [])
    inventory: list[dict[str, object]] = []
    for project in projects if isinstance(projects, list) else []:
        if not isinstance(project, dict):
            continue
        source_dir = str(project.get("skillSourceDir") or "").strip()
        inventory.append(
            {
                "id": str(project.get("id") or "").strip(),
                "skillSourceDir": source_dir,
                "windowsProjectRoot": str(project.get("windowsProjectRoot") or "").strip(),
                "wslProjectRoot": str(project.get("wslProjectRoot") or "").strip(),
                "skills": scanner.scan_skills(source_dir) if source_dir else [],
                "sourceMissing": bool(source_dir and not Path(source_dir).exists()),
            }
        )
    return [project for project in inventory if project["id"]]


def _project_inventory_index(
    inventory: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    return {project["id"]: project for project in inventory}


def _project_resource_map(config: dict[str, object]) -> dict[str, dict[str, dict[str, list[str]]]]:
    resources = config.get("resources", {})
    if not isinstance(resources, dict):
        return {}
    project_skills = resources.get("projectSkills")
    return project_skills if isinstance(project_skills, dict) else {}


def _skill_entry(
    project: dict[str, object],
    skill_name: str,
) -> dict[str, object]:
    scanned_skills = project.get("skills", [])
    skill_index = {
        item["name"]: item
        for item in scanned_skills
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    entry = skill_index.get(skill_name)
    if entry is not None:
        return entry
    source_dir = str(project.get("skillSourceDir") or "").strip()
    return {
        "name": skill_name,
        "path": str(Path(source_dir) / skill_name) if source_dir else skill_name,
        "isDirectory": True,
        "description": "",
        "descriptionSource": "",
    }


def _resolve_environment_root(
    project: dict[str, object],
    environment: dict[str, object],
) -> dict[str, object]:
    if environment["id"] == "windows":
        raw_root = str(project.get("windowsProjectRoot") or "").strip()
        if not raw_root:
            return {"available": False, "state": "environment_error", "message": "未配置 Windows 项目目录"}
        resolved_root = expand_windows_path(raw_root)
        if not Path(resolved_root).exists():
            return {"available": False, "state": "environment_error", "message": "Windows 项目目录不存在"}
        return {"available": True, "projectRoot": resolved_root}

    meta = environment.get("meta", {})
    if environment.get("error"):
        return {"available": False, "state": "environment_error", "message": environment["error"]}
    if not isinstance(meta, dict) or not meta.get("available"):
        return {
            "available": False,
            "state": "environment_error",
            "message": "未能解析 WSL 发行版或主目录",
        }
    raw_root = str(project.get("wslProjectRoot") or "").strip()
    if not raw_root:
        return {"available": False, "state": "environment_error", "message": "未配置 WSL 项目目录"}
    linux_root = expand_posix_home_path(raw_root, str(meta.get("homeDir") or ""))
    project_root = linux_path_to_unc(str(meta.get("selectedDistro") or ""), linux_root)
    if not Path(project_root).exists():
        return {"available": False, "state": "environment_error", "message": "WSL 项目目录不存在"}
    return {"available": True, "projectRoot": project_root}


def _target_base_dir(project_root: str, tool_id: str) -> str:
    return str(Path(project_root, *PROJECT_SKILL_TARGET_SEGMENTS[tool_id]))


def _configured_targets(
    assignments: dict[str, dict[str, dict[str, list[str]]]],
    project_id: str,
    skill_name: str,
) -> dict[str, list[str]]:
    project_map = assignments.get(project_id)
    if not isinstance(project_map, dict):
        return {}
    targets = project_map.get(skill_name)
    return targets if isinstance(targets, dict) else {}


def _detected_targets(
    project: dict[str, object],
    skill: dict[str, object],
    environment_list: dict[str, object],
) -> dict[str, list[str]]:
    detected: dict[str, list[str]] = {}
    for environment_id in ENVIRONMENT_IDS:
        environment = environment_list.get(environment_id)
        if not isinstance(environment, dict):
            continue
        availability = _resolve_environment_root(project, environment)
        if not availability["available"]:
            continue
        tools: list[str] = []
        for tool_id in PROJECT_SKILL_TOOL_IDS:
            target_path = str(Path(_target_base_dir(availability["projectRoot"], tool_id)) / skill["name"])
            if file_sync.has_path(target_path):
                tools.append(tool_id)
        if tools:
            detected[environment_id] = tools
    return detected


def _build_entries(
    config: dict[str, object],
    project: dict[str, object],
    skill: dict[str, object],
    targets: dict[str, list[str]],
    environment_list: dict[str, object],
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for environment_id in ENVIRONMENT_IDS:
        environment = environment_list.get(environment_id)
        if not isinstance(environment, dict):
            continue
        selected_tools = targets.get(environment_id, [])
        if not selected_tools:
            continue
        availability = _resolve_environment_root(project, environment)
        if not availability["available"]:
            for tool_id in selected_tools:
                entries.append(
                    {
                        "environmentId": environment_id,
                        "toolId": tool_id,
                        "state": availability["state"],
                        "message": availability["message"],
                        "targetPath": None,
                        "targetExists": False,
                    }
                )
            continue
        for tool_id in selected_tools:
            target_path = str(Path(_target_base_dir(availability["projectRoot"], tool_id)) / skill["name"])
            state = describe_target_state(config["syncMode"], skill["path"], target_path)
            entries.append(
                {
                    "environmentId": environment_id,
                    "toolId": tool_id,
                    "targetPath": target_path,
                    "targetExists": file_sync.has_path(target_path),
                    **state,
                }
            )
    return entries


def _summarize_entries(
    entries: list[dict[str, object]],
    configured: dict[str, list[str]],
    detected: dict[str, list[str]],
) -> tuple[str, str]:
    has_configured = any(configured.get(environment_id) for environment_id in ENVIRONMENT_IDS)
    has_detected = any(detected.get(environment_id) for environment_id in ENVIRONMENT_IDS)
    if not has_configured:
        return ("detected", "已检测到目标") if has_detected else ("idle", "未分配")
    if not entries:
        return "partial", "已分配但尚无状态明细"
    summary = aggregate_states(entries)
    return str(summary["state"]), str(summary["message"])


def build_project_skill_statuses(
    config: dict[str, object],
    environment_list: dict[str, object],
) -> list[dict[str, object]]:
    inventory = scan_project_skill_inventory(config)
    assignments = _project_resource_map(config)
    projects: list[dict[str, object]] = []
    for project in inventory:
        project_id = project["id"]
        project_assignments = assignments.get(project_id, {}) if isinstance(assignments.get(project_id), dict) else {}
        skill_names = {
            skill["name"]
            for skill in project.get("skills", [])
            if isinstance(skill, dict) and isinstance(skill.get("name"), str)
        } | set(project_assignments.keys())
        skills: list[dict[str, object]] = []
        for skill_name in sorted(skill_names):
            skill = _skill_entry(project, skill_name)
            configured = _configured_targets(assignments, project_id, skill_name)
            detected = _detected_targets(project, skill, environment_list)
            entries = _build_entries(config, project, skill, configured, environment_list)
            summary_state, summary_message = _summarize_entries(entries, configured, detected)
            skills.append(
                {
                    "projectId": project_id,
                    "name": skill_name,
                    "path": skill["path"],
                    "isDirectory": bool(skill.get("isDirectory")),
                    "description": str(skill.get("description") or ""),
                    "descriptionSource": str(skill.get("descriptionSource") or ""),
                    "configuredTargets": configured,
                    "detectedTargets": detected,
                    "effectiveTargets": merge_environment_targets(configured, detected),
                    "entries": entries,
                    "summaryState": summary_state,
                    "summaryMessage": summary_message,
                }
            )
        projects.append(
            {
                "id": project_id,
                "skillSourceDir": project["skillSourceDir"],
                "windowsProjectRoot": project["windowsProjectRoot"],
                "wslProjectRoot": project["wslProjectRoot"],
                "sourceMissing": project["sourceMissing"],
                "skills": skills,
                "summaryState": "source_missing" if project["sourceMissing"] else ("idle" if not skills else "healthy"),
                "summaryMessage": (
                    "源目录不存在"
                    if project["sourceMissing"]
                    else (f"共 {len(skills)} 个 Skills" if skills else "无 Skills")
                ),
            }
        )
    return projects


def _requested_items(
    assignments: dict[str, dict[str, dict[str, list[str]]]],
    requested_items: list[dict[str, str]] | None,
) -> list[tuple[str, str]]:
    if requested_items is None:
        items: list[tuple[str, str]] = []
        for project_id, project_assignments in assignments.items():
            if not isinstance(project_assignments, dict):
                continue
            for skill_name in project_assignments:
                items.append((project_id, skill_name))
        return items
    items = []
    for item in requested_items:
        if not isinstance(item, dict):
            continue
        project_id = str(item.get("projectId") or "").strip()
        skill_name = str(item.get("skillName") or "").strip()
        if project_id and skill_name:
            items.append((project_id, skill_name))
    return items


def sync_project_skills(
    config: dict[str, object],
    environment_list: dict[str, object],
    inventory: list[dict[str, object]],
    requested_items: list[dict[str, str]] | None = None,
    assignments_override: dict[str, dict[str, dict[str, list[str]]]] | None = None,
) -> list[dict[str, object]]:
    assignments = assignments_override or _project_resource_map(config)
    inventory_index = _project_inventory_index(inventory)
    results: list[dict[str, object]] = []
    for project_id, skill_name in _requested_items(assignments, requested_items):
        project = inventory_index.get(project_id)
        if project is None:
            results.append(
                {
                    "projectId": project_id,
                    "name": skill_name,
                    "success": False,
                    "skipped": True,
                    "message": "未找到项目定义",
                }
            )
            continue
        skill = _skill_entry(project, skill_name)
        configured = _configured_targets(assignments, project_id, skill_name)
        for environment_id in ENVIRONMENT_IDS:
            environment = environment_list.get(environment_id)
            if not isinstance(environment, dict):
                continue
            selected_tools = configured.get(environment_id, [])
            if not selected_tools:
                continue
            availability = _resolve_environment_root(project, environment)
            if not availability["available"]:
                for tool_id in selected_tools:
                    results.append(
                        {
                            "projectId": project_id,
                            "name": skill_name,
                            "environmentId": environment_id,
                            "toolId": tool_id,
                            "success": False,
                            "skipped": True,
                            "message": availability["message"],
                        }
                    )
                continue
            for tool_id in selected_tools:
                target_path = str(Path(_target_base_dir(availability["projectRoot"], tool_id)) / skill_name)
                result = sync_entry(config["syncMode"], skill["path"], target_path, bool(skill.get("isDirectory")))
                results.append(
                    {
                        "projectId": project_id,
                        "name": skill_name,
                        "environmentId": environment_id,
                        "toolId": tool_id,
                        "targetPath": target_path,
                        **result,
                    }
                )
    return results


def remove_project_skills(
    config: dict[str, object],
    environment_list: dict[str, object],
    inventory: list[dict[str, object]],
    requested_items: list[dict[str, str]],
    assignments_override: dict[str, dict[str, dict[str, list[str]]]] | None = None,
) -> list[dict[str, object]]:
    assignments = assignments_override or _project_resource_map(config)
    inventory_index = _project_inventory_index(inventory)
    results: list[dict[str, object]] = []
    for project_id, skill_name in _requested_items(assignments, requested_items):
        project = inventory_index.get(project_id)
        if project is None:
            results.append(
                {
                    "projectId": project_id,
                    "name": skill_name,
                    "success": False,
                    "skipped": True,
                    "message": "未找到项目定义",
                }
            )
            continue
        configured = _configured_targets(assignments, project_id, skill_name)
        for environment_id in ENVIRONMENT_IDS:
            environment = environment_list.get(environment_id)
            if not isinstance(environment, dict):
                continue
            selected_tools = configured.get(environment_id, [])
            if not selected_tools:
                continue
            availability = _resolve_environment_root(project, environment)
            if not availability["available"]:
                for tool_id in selected_tools:
                    results.append(
                        {
                            "projectId": project_id,
                            "name": skill_name,
                            "environmentId": environment_id,
                            "toolId": tool_id,
                            "success": False,
                            "skipped": True,
                            "message": availability["message"],
                        }
                    )
                continue
            for tool_id in selected_tools:
                target_path = str(Path(_target_base_dir(availability["projectRoot"], tool_id)) / skill_name)
                results.append(
                    {
                        "projectId": project_id,
                        "name": skill_name,
                        "environmentId": environment_id,
                        "toolId": tool_id,
                        "targetPath": target_path,
                        **remove_target(target_path),
                    }
                )
    return results
