from dataclasses import dataclass, replace
from typing import Callable
from pathlib import Path, PurePosixPath

from .config_service import load_config, normalize_config_shape, save_config
from .environment_service import (
    get_default_wsl_distro,
    get_wsl_home_dir,
    list_wsl_distros,
    resolve_environment_targets,
)
from .global_rule_runtime_service import build_global_rule_statuses
from .global_rule_state_service import load_global_rules, save_global_rules
from .global_rule_sync_service import sync_global_rules as sync_global_rule_targets
from .resource_operations import (
    build_resource_statuses,
    cleanup_invalid_resources,
    upgrade_configured_resources,
    sync_configured_resources,
)
from .remove_operations import remove_configured_resources
from .resource_service import scan_resources
from .runtime_service import build_environment_list, build_wsl_runtime
from .updater import build_update_tool_statuses, update_all_tools
from .skill_upstream_state_service import load_skill_upstreams, save_skill_upstreams
from .workflow_state_service import load_workflow_state, save_workflow_state
from .workflow_service import scan_workflow_statuses, execute_workflow_action
from .github_skill_upstream import (
    derive_child_tree_url,
    get_latest_commit_sha,
    infer_skill_name_from_github_url,
    install_github_tree_to_dir,
    parse_github_tree_url,
    validate_skill_name,
)


def _replace_resource_map(
    config: dict[str, object],
    kind: str,
    assignments: dict[str, dict[str, list[str]]],
) -> dict[str, object]:
    return save_config(
        normalize_config_shape(
            {
                **config,
                "resources": {
                    **config["resources"],
                    kind: assignments,
                },
            }
        )
    )


def _save_settings(config: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    next_config = normalize_config_shape(
        {
            **config,
            **patch,
            "environments": {
                **config["environments"],
                **patch.get("environments", {}),
            },
            "sourceDirs": {
                **config["sourceDirs"],
                **patch.get("sourceDirs", {}),
            },
        }
    )
    return save_config(next_config)


def _resolve_skill_source_url(skill_name: str, raw_url: str) -> tuple[str, object]:
    normalized_url = str(raw_url or "").strip()
    source = parse_github_tree_url(normalized_url)
    leaf = str(PurePosixPath(source.path).name) if source.path else ""
    if source.is_file:
        inferred_name = infer_skill_name_from_github_url(normalized_url) or ""
        if inferred_name != skill_name:
            raise ValueError(f"单文件 URL 只能绑定同名 skill：{inferred_name or '未识别'}")
        return normalized_url, source
    if leaf != skill_name:
        normalized_url = derive_child_tree_url(normalized_url, skill_name)
        source = parse_github_tree_url(normalized_url)
    return normalized_url, source


@dataclass(frozen=True)
class ServiceDependencies:
    get_default_wsl_distro: Callable = get_default_wsl_distro
    get_wsl_home_dir: Callable = get_wsl_home_dir
    list_wsl_distros: Callable = list_wsl_distros
    load_config: Callable = load_config
    load_global_rules: Callable = load_global_rules
    load_skill_upstreams: Callable = load_skill_upstreams
    resolve_environment_targets: Callable = resolve_environment_targets
    save_config: Callable = save_config
    save_global_rules: Callable = save_global_rules
    save_skill_upstreams: Callable = save_skill_upstreams
    load_workflow_state: Callable = load_workflow_state
    save_workflow_state: Callable = save_workflow_state
    update_all_tools: Callable = update_all_tools


@dataclass(frozen=True)
class AppService:
    deps: ServiceDependencies

    def cleanup_invalid(self) -> dict[str, object]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return cleanup_invalid_resources(config, environments, self.deps.save_config)

    def get_config(self) -> dict[str, object]:
        return self.deps.load_config()

    def get_status(self) -> dict[str, object]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return {
            "config": config,
            "environments": environments,
            "skills": build_resource_statuses(config, "skills", environments),
            "commands": build_resource_statuses(config, "commands", environments),
        }

    def get_global_rules(self) -> dict[str, object]:
        return self.deps.load_global_rules()

    def get_global_rule_status(self) -> list[dict[str, object]]:
        config = self.deps.load_config()
        global_rules = self.deps.load_global_rules()
        environments = build_environment_list(config, self._runtime_deps())
        return build_global_rule_statuses(global_rules, environments)

    def get_wsl_distros(self) -> dict[str, object]:
        return build_wsl_runtime(self.deps.load_config(), self._runtime_deps())

    def save_config(self, patch: dict[str, object]) -> dict[str, object]:
        return _save_settings(self.deps.load_config(), patch)

    def save_global_rule_profiles(self, payload: dict[str, object]) -> dict[str, object]:
        current = self.deps.load_global_rules()
        profiles = payload.get("profiles")
        return self.deps.save_global_rules(
            {
                "profiles": profiles,
                "assignments": current["assignments"],
            }
        )

    def save_global_rule_assignments(
        self,
        assignments: dict[str, dict[str, str | None]],
    ) -> dict[str, object]:
        current = self.deps.load_global_rules()
        return self.deps.save_global_rules(
            {
                "profiles": current["profiles"],
                "assignments": assignments,
            }
        )

    def scan_resources(self, kind: str) -> list[dict[str, object]]:
        return scan_resources(self.deps.load_config(), kind)

    def get_skill_upstreams(self) -> dict[str, dict[str, object]]:
        return self.deps.load_skill_upstreams()

    def set_skill_upstream_url(
        self,
        names: list[str],
        url: str,
    ) -> dict[str, dict[str, object]]:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            raise ValueError("URL 不能为空。")
        upstreams = self.deps.load_skill_upstreams()
        next_upstreams = {**upstreams}
        for name in names:
            skill_name = validate_skill_name(name)
            skill_url, source = _resolve_skill_source_url(skill_name, normalized_url)
            previous = next_upstreams.get(skill_name, {}) if isinstance(next_upstreams.get(skill_name), dict) else {}
            if previous.get("url") == skill_url and previous.get("installedCommit"):
                next_upstreams[skill_name] = {**previous, "url": skill_url}
            else:
                latest = get_latest_commit_sha(source)
                next_upstreams[skill_name] = {"url": skill_url, "installedCommit": latest}
        return self.deps.save_skill_upstreams(next_upstreams)

    def add_skill_from_url(self, name: str, url: str) -> dict[str, object]:
        config = self.deps.load_config()
        source_dir = config["sourceDirs"]["skills"]
        normalized_url = str(url or "").strip()
        if not normalized_url:
            raise ValueError("URL 不能为空。")
        resolved_name = str(name or "").strip() or infer_skill_name_from_github_url(normalized_url) or ""
        skill_name = validate_skill_name(resolved_name)
        normalized_url, source = _resolve_skill_source_url(skill_name, normalized_url)
        installed_commit = install_github_tree_to_dir(source, Path(source_dir) / skill_name)
        upstreams = self.deps.load_skill_upstreams()
        next_upstreams = {**upstreams, skill_name: {"url": normalized_url, "installedCommit": installed_commit}}
        self.deps.save_skill_upstreams(next_upstreams)
        return {"name": skill_name, "url": normalized_url, "installedCommit": installed_commit}

    def check_skill_updates(self, names: list[str] | None = None) -> list[dict[str, object]]:
        upstreams = self.deps.load_skill_upstreams()
        selected = names or sorted(upstreams.keys())
        dirty = False
        results: list[dict[str, object]] = []
        for name in selected:
            skill_name = validate_skill_name(name)
            entry = upstreams.get(skill_name)
            if not isinstance(entry, dict) or not entry.get("url"):
                results.append(
                    {
                        "name": skill_name,
                        "configured": False,
                        "installedCommit": None,
                        "latestCommit": None,
                        "updateAvailable": False,
                        "message": "未配置更新 URL",
                    }
                )
                continue
            url = str(entry.get("url") or "").strip()
            installed = str(entry.get("installedCommit") or "").strip() or None
            source = parse_github_tree_url(url)
            latest = get_latest_commit_sha(source)
            if installed is None and latest:
                installed = latest
                upstreams[skill_name] = {**entry, "installedCommit": installed}
                dirty = True
            results.append(
                {
                    "name": skill_name,
                    "configured": True,
                    "url": url,
                    "installedCommit": installed,
                    "latestCommit": latest,
                    "updateAvailable": bool(latest and latest != installed),
                    "message": "有更新" if latest and latest != installed else "已是最新",
                }
            )
        if dirty:
            self.deps.save_skill_upstreams(upstreams)
        return results

    def upgrade_skill_sources(self, names: list[str]) -> list[dict[str, object]]:
        config = self.deps.load_config()
        source_dir = config["sourceDirs"]["skills"]
        upstreams = self.deps.load_skill_upstreams()
        next_upstreams = {**upstreams}
        results: list[dict[str, object]] = []
        for name in names:
            skill_name = validate_skill_name(name)
            entry = upstreams.get(skill_name)
            if not isinstance(entry, dict) or not entry.get("url"):
                raise ValueError(f"未配置更新 URL：{skill_name}")
            url = str(entry.get("url") or "").strip()
            source = parse_github_tree_url(url)
            installed_commit = install_github_tree_to_dir(source, Path(source_dir) / skill_name)
            next_upstreams[skill_name] = {"url": url, "installedCommit": installed_commit}
            results.append(
                {
                    "name": skill_name,
                    "url": url,
                    "installedCommit": installed_commit,
                    "latestCommit": installed_commit,
                    "success": True,
                    "message": "已更新",
                }
            )
        self.deps.save_skill_upstreams(next_upstreams)
        return results

    def replace_resource_map(
        self,
        kind: str,
        assignments: dict[str, dict[str, list[str]]],
    ) -> dict[str, object]:
        return _replace_resource_map(self.deps.load_config(), kind, assignments)

    def sync_all(self) -> dict[str, list[dict[str, object]]]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return {
            "skills": sync_configured_resources(config, "skills", environments),
            "commands": sync_configured_resources(config, "commands", environments),
        }

    def sync_resources(
        self,
        kind: str,
        names: list[str] | None = None,
        assignments: dict[str, dict[str, list[str]]] | None = None,
    ) -> list[dict[str, object]]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return sync_configured_resources(config, kind, environments, names, assignments)

    def upgrade_resources(
        self,
        kind: str,
        names: list[str] | None = None,
        assignments: dict[str, dict[str, list[str]]] | None = None,
    ) -> list[dict[str, object]]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return upgrade_configured_resources(config, kind, environments, names, assignments)

    def remove_resources(
        self,
        kind: str,
        names: list[str] | None = None,
        assignments: dict[str, dict[str, list[str]]] | None = None,
    ) -> list[dict[str, object]]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        return remove_configured_resources(config, kind, environments, names, assignments)

    def update_tools(self, target_versions: dict[str, str] | None = None) -> list[dict[str, object]]:
        config = self.deps.load_config()
        wsl_runtime = build_wsl_runtime(config, self._runtime_deps())
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        return self.deps.update_all_tools(
            config["updateTools"],
            wsl_distro=wsl_distro,
            target_versions=target_versions,
        )

    def update_tool(self, name: str, target_version: str | None = None) -> list[dict[str, object]]:
        config = self.deps.load_config()
        tools = config["updateTools"]
        if name not in tools:
            raise ValueError(f"未找到更新定义：{name}")
        wsl_runtime = build_wsl_runtime(config, self._runtime_deps())
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        target_versions = {name: target_version} if target_version else None
        return self.deps.update_all_tools(
            {name: tools[name]},
            wsl_distro=wsl_distro,
            target_versions=target_versions,
        )

    def get_update_tool_statuses(
        self,
        config: dict[str, object],
        wsl_runtime: dict[str, object],
    ) -> dict[str, dict[str, object]]:
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        tools = config["updateTools"]
        return build_update_tool_statuses(tools, wsl_distro=wsl_distro)

    def sync_global_rules(
        self,
        targets: list[dict[str, str]] | None = None,
        assignments: dict[str, dict[str, str | None]] | None = None,
    ) -> list[dict[str, object]]:
        config = self.deps.load_config()
        global_rules = self.deps.load_global_rules()
        if assignments is not None:
            global_rules = self.deps.save_global_rules(
                {
                    "profiles": global_rules["profiles"],
                    "assignments": assignments,
                }
            )
        environments = build_environment_list(config, self._runtime_deps())
        return sync_global_rule_targets(global_rules, environments, targets)

    def get_workflow_statuses(self) -> list[dict[str, object]]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        workflow_state = self.deps.load_workflow_state()
        return scan_workflow_statuses(environments, workflow_state)

    def workflow_action(
        self,
        workflow_id: str,
        target_key: str,
        action: str,
    ) -> dict[str, object]:
        config = self.deps.load_config()
        environments = build_environment_list(config, self._runtime_deps())
        workflow_state = self.deps.load_workflow_state()
        return execute_workflow_action(
            workflow_id, target_key, action, environments,
            workflow_state, self.deps.save_workflow_state,
        )

    def _runtime_deps(self) -> dict[str, Callable]:
        return {
            "get_default_wsl_distro": self.deps.get_default_wsl_distro,
            "get_wsl_home_dir": self.deps.get_wsl_home_dir,
            "list_wsl_distros": self.deps.list_wsl_distros,
            "resolve_environment_targets": self.deps.resolve_environment_targets,
        }


def create_app_service(overrides: dict[str, Callable] | None = None) -> AppService:
    deps = ServiceDependencies()
    for name, value in (overrides or {}).items():
        deps = replace(deps, **{name: value})
    return AppService(deps)
