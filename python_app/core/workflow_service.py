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


def scan_workflow_statuses(
    environments: dict[str, object],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
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
                    targets[target_key] = {
                        "available": status.available,
                        "installed": status.installed,
                        "enabled": status.enabled,
                        "version": status.version,
                        "installedCommit": status.installed_commit,
                        "error": status.error,
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

    action_map = {
        "install": handler.install,
        "uninstall": handler.uninstall,
        "enable": handler.enable,
        "disable": handler.disable,
        "upgrade": handler.upgrade,
    }
    fn = action_map.get(action)
    if fn is None:
        raise ValueError(f"未知操作: {action}")

    result = fn(ctx)

    if action in ("install", "upgrade") and result.get("success"):
        _update_state_after_install(
            workflow_state, save_state_fn, workflow_id, target_key, result,
        )
    elif action == "uninstall" and result.get("success"):
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
