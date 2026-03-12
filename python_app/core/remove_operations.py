from pathlib import Path

from .cleanup_targets import get_cleanup_targets
from .resource_service import (
    expand_resource_items,
    get_configured_resources,
    get_resource_catalog,
    get_resource_entry,
)
from .runtime_service import build_availability
from .sync_engine import remove_target


def remove_configured_resources(
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
    details: list[dict[str, object]] = []
    for name in names:
        resource = get_resource_entry(config, kind, name, index)
        configured_targets = configured.get(name, {})
        for environment in environment_list.values():
            for tool_id in configured_targets.get(environment["id"], []):
                availability = build_availability(environment, kind, tool_id)
                base_target = environment["targets"][kind][tool_id]
                if not availability["available"]:
                    details.append(
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
                items = expand_resource_items(config, kind, resource, tool_id)
                targets = [str(Path(base_target) / item["name"]) for item in items] if base_target else []
                entry = {"targets": targets, "targetPath": base_target}
                for target_path in get_cleanup_targets(kind, name, entry):
                    details.append(
                        {
                            "kind": kind,
                            "name": name,
                            "toolId": tool_id,
                            "environmentId": environment["id"],
                            "targetPath": target_path,
                            **remove_target(target_path),
                        }
                    )
    return details

