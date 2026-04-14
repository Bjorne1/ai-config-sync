from __future__ import annotations

from pathlib import Path

from .workflow_handlers import TargetContext, WorkflowHandler
from .workflow_registry import WORKFLOW_REGISTRY


WORKFLOW_TOOL_IDS = ("claude", "codex")
WORKFLOW_ENVIRONMENT_IDS = ("windows", "wsl")


def _build_target_context(
    environment_id: str,
    tool_id: str,
    environments: dict[str, object],
) -> TargetContext | None:
    env = environments.get(environment_id)
    if not isinstance(env, dict):
        return None
    roots = env.get("roots")
    if not isinstance(roots, dict):
        return None
    root_path = roots.get(tool_id)
    if not root_path:
        return None
    home_dir = str(Path(root_path).parent)
    wsl_distro = None
    if environment_id == "wsl":
        meta = env.get("meta")
        if isinstance(meta, dict):
            wsl_distro = meta.get("selectedDistro")
    return TargetContext(
        environment_id=environment_id,
        tool_id=tool_id,
        home_dir=home_dir,
        wsl_distro=wsl_distro,
    )


def _get_handler(workflow_id: str, tool_id: str) -> WorkflowHandler:
    definition = WORKFLOW_REGISTRY.get(workflow_id)
    if not definition:
        raise ValueError(f"未注册的工作流: {workflow_id}")
    if tool_id not in definition.supported_tools:
        raise ValueError(f"工作流 {workflow_id} 不支持工具: {tool_id}")
    return definition.handler_factory(tool_id)


def _parse_target_key(target_key: str) -> tuple[str, str]:
    parts = target_key.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"无效的 target_key: {target_key}")
    return parts[0], parts[1]


def _normalize_workflow_action(action: str) -> str:
    return _parse_workflow_action(action)[0]


def _parse_workflow_action(action: str) -> tuple[str, bool | None, bool | None]:
    parts = [segment.strip() for segment in action.split("|") if segment.strip()]
    if not parts:
        raise ValueError("工作流操作不能为空")
    base_action = parts[0]
    force_agents_overwrite: bool | None = None
    supplement_rules: bool | None = None
    for part in parts[1:]:
        key, sep, raw_value = part.partition("=")
        if sep != "=":
            raise ValueError(f"无效的操作参数: {part}")
        value = raw_value.strip()
        if value not in {"0", "1"}:
            raise ValueError(f"无效的操作参数值: {part}")
        enabled = value == "1"
        if key == "force":
            force_agents_overwrite = enabled
            continue
        if key == "supplement":
            supplement_rules = enabled
            continue
        raise ValueError(f"未知的操作参数: {key}")
    return base_action, force_agents_overwrite, supplement_rules


def scan_workflow_statuses(
    environments: dict[str, object],
    workflow_state: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    state = workflow_state or {}
    for workflow_id, definition in WORKFLOW_REGISTRY.items():
        targets: dict[str, dict[str, object]] = {}
        for env_id in WORKFLOW_ENVIRONMENT_IDS:
            for tool_id in definition.supported_tools:
                target_key = f"{env_id}:{tool_id}"
                ctx = _build_target_context(env_id, tool_id, environments)
                if ctx is None:
                    env = environments.get(env_id, {})
                    error = env.get("error") if isinstance(env, dict) else None
                    targets[target_key] = {
                        "available": False,
                        "installed": False,
                        "enabled": False,
                        "version": None,
                        "error": error or "环境不可用",
                    }
                    continue
                handler = definition.handler_factory(tool_id)
                try:
                    status = handler.detect_status(ctx)
                    saved_target = (
                        state.get(workflow_id, {}).get("targets", {}).get(target_key, {})
                        if isinstance(state.get(workflow_id, {}), dict)
                        else {}
                    )
                    saved_commit = None
                    saved_version = None
                    if isinstance(saved_target, dict):
                        saved_commit = str(saved_target.get("installedCommit") or "").strip() or None
                        saved_version = str(saved_target.get("installedVersion") or "").strip() or None
                    targets[target_key] = {
                        "available": status.available,
                        "installed": status.installed,
                        "enabled": status.enabled,
                        "version": status.version or (saved_version if status.installed else None),
                        "installedCommit": status.installed_commit or (saved_commit if status.installed else None),
                        "error": status.error,
                        "skillsLinkable": status.skills_linkable,
                        "skillsLinked": status.skills_linked,
                        "skillsTotal": status.skills_total,
                        **status.metadata,
                    }
                except Exception as exc:
                    targets[target_key] = {
                        "available": False,
                        "installed": False,
                        "enabled": False,
                        "version": None,
                        "error": str(exc),
                    }
        results.append({
            "workflowId": workflow_id,
            "label": definition.label,
            "description": definition.description,
            "repoUrl": definition.repo_url,
            "supportedTools": list(definition.supported_tools),
            "targets": targets,
        })
    return results


def execute_workflow_action(
    workflow_id: str,
    target_key: str,
    action: str,
    environments: dict[str, object],
    workflow_state: dict[str, dict[str, object]],
    save_state_fn: object,
) -> dict[str, object]:
    env_id, tool_id = _parse_target_key(target_key)
    handler = _get_handler(workflow_id, tool_id)
    ctx = _build_target_context(env_id, tool_id, environments)
    if ctx is None:
        raise RuntimeError(f"无法解析目标环境: {target_key}")
    normalized_action, force_agents_overwrite, supplement_rules = _parse_workflow_action(action)

    install_force = getattr(handler, "install_with_options", None)
    enable_force = getattr(handler, "enable_with_options", None)
    upgrade_force = getattr(handler, "upgrade_with_options", None)

    action_map = {
        "install": handler.install,
        "uninstall": handler.uninstall,
        "enable": handler.enable,
        "disable": handler.disable,
        "upgrade": handler.upgrade,
        "link_skills": handler.link_skills,
        "unlink_skills": handler.unlink_skills,
    }
    if normalized_action == "install" and callable(install_force):
        result = install_force(
            ctx,
            force_agents_overwrite=force_agents_overwrite,
            supplement_rules=bool(supplement_rules),
        )
    elif normalized_action == "enable" and callable(enable_force):
        result = enable_force(
            ctx,
            force_agents_overwrite=force_agents_overwrite,
            supplement_rules=bool(supplement_rules),
        )
    elif normalized_action == "upgrade" and callable(upgrade_force):
        result = upgrade_force(
            ctx,
            force_agents_overwrite=force_agents_overwrite,
            supplement_rules=bool(supplement_rules),
        )
    else:
        fn = action_map.get(normalized_action)
        if fn is None:
            raise ValueError(f"未知操作: {action}")
        result = fn(ctx)

    if normalized_action in ("install", "upgrade") and result.get("success"):
        _update_state_after_install(
            workflow_state, save_state_fn, workflow_id, target_key, result,
        )
    elif normalized_action == "uninstall" and result.get("success"):
        _update_state_after_uninstall(
            workflow_state, save_state_fn, workflow_id, target_key,
        )

    return result


def _update_state_after_install(
    workflow_state: dict, save_state_fn: object, workflow_id: str,
    target_key: str, result: dict,
) -> None:
    from datetime import datetime, timezone
    wf = dict(workflow_state.get(workflow_id, {}))
    targets = dict(wf.get("targets", {}))
    targets[target_key] = {
        "installedCommit": result.get("commit", ""),
        "installedVersion": result.get("version", ""),
        "installedAt": datetime.now(timezone.utc).isoformat(),
    }
    wf["targets"] = targets
    next_state = {**workflow_state, workflow_id: wf}
    save_state_fn(next_state)


def _update_state_after_uninstall(
    workflow_state: dict, save_state_fn: object, workflow_id: str,
    target_key: str,
) -> None:
    wf = dict(workflow_state.get(workflow_id, {}))
    targets = dict(wf.get("targets", {}))
    targets.pop(target_key, None)
    if targets:
        wf["targets"] = targets
        next_state = {**workflow_state, workflow_id: wf}
    else:
        next_state = {k: v for k, v in workflow_state.items() if k != workflow_id}
    save_state_fn(next_state)
