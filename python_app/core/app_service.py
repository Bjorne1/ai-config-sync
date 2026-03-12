from dataclasses import dataclass, replace
from typing import Callable

from .config_service import load_config, normalize_config_shape, save_config
from .environment_service import (
    get_default_wsl_distro,
    get_wsl_home_dir,
    list_wsl_distros,
    resolve_environment_targets,
)
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


@dataclass(frozen=True)
class ServiceDependencies:
    get_default_wsl_distro: Callable = get_default_wsl_distro
    get_wsl_home_dir: Callable = get_wsl_home_dir
    list_wsl_distros: Callable = list_wsl_distros
    load_config: Callable = load_config
    resolve_environment_targets: Callable = resolve_environment_targets
    save_config: Callable = save_config
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

    def get_wsl_distros(self) -> dict[str, object]:
        return build_wsl_runtime(self.deps.load_config(), self._runtime_deps())

    def save_config(self, patch: dict[str, object]) -> dict[str, object]:
        return _save_settings(self.deps.load_config(), patch)

    def scan_resources(self, kind: str) -> list[dict[str, object]]:
        return scan_resources(self.deps.load_config(), kind)

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

    def update_tools(self) -> list[dict[str, object]]:
        config = self.deps.load_config()
        wsl_runtime = build_wsl_runtime(config, self._runtime_deps())
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        return self.deps.update_all_tools(config["updateTools"], wsl_distro=wsl_distro)

    def update_tool(self, name: str) -> list[dict[str, object]]:
        config = self.deps.load_config()
        tools = config["updateTools"]
        if name not in tools:
            raise ValueError(f"未找到更新定义：{name}")
        wsl_runtime = build_wsl_runtime(config, self._runtime_deps())
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        return self.deps.update_all_tools({name: tools[name]}, wsl_distro=wsl_distro)

    def get_update_tool_statuses(
        self,
        config: dict[str, object],
        wsl_runtime: dict[str, object],
    ) -> dict[str, dict[str, object]]:
        wsl_distro = wsl_runtime["selectedDistro"] if wsl_runtime.get("available") else None
        tools = config["updateTools"]
        return build_update_tool_statuses(tools, wsl_distro=wsl_distro)

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
