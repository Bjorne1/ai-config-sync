from pathlib import Path

from . import scanner


def get_source_dir(config: dict[str, object], kind: str) -> str:
    return config["sourceDirs"][kind]


def scan_resources(config: dict[str, object], kind: str) -> list[dict[str, object]]:
    source_dir = get_source_dir(config, kind)
    return scanner.scan_skills(source_dir) if kind == "skills" else scanner.scan_commands(source_dir)


def _index_resources(resources: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {resource["name"]: resource for resource in resources}


def get_resource_catalog(config: dict[str, object]) -> dict[str, object]:
    skills = scan_resources(config, "skills")
    commands = scan_resources(config, "commands")
    return {
        "skills": skills,
        "commands": commands,
        "skillIndex": _index_resources(skills),
        "commandIndex": _index_resources(commands),
    }


def get_configured_resources(config: dict[str, object], kind: str) -> dict[str, dict[str, list[str]]]:
    return config["resources"].get(kind, {})


def list_managed_names(
    config: dict[str, object],
    kind: str,
    index: dict[str, dict[str, object]],
) -> list[str]:
    configured_names = set(get_configured_resources(config, kind).keys())
    return sorted(set(index.keys()) | configured_names)


def build_virtual_resource(config: dict[str, object], kind: str, name: str) -> dict[str, object]:
    return {
        "name": name,
        "path": str(Path(get_source_dir(config, kind)) / name),
        "isDirectory": False,
        "children": [],
    }


def get_resource_entry(
    config: dict[str, object],
    kind: str,
    name: str,
    index: dict[str, dict[str, object]],
) -> dict[str, object]:
    return index.get(name) or build_virtual_resource(config, kind, name)


def expand_resource_items(
    config: dict[str, object],
    kind: str,
    resource: dict[str, object],
    tool_id: str,
) -> list[dict[str, object]]:
    if kind == "skills":
        return [
            {
                "name": resource["name"],
                "sourcePath": resource["path"],
                "isDirectory": resource["isDirectory"],
            }
        ]
    tools = config["commandSubfolderSupport"]["tools"]
    supports_subfolders = tools.get(tool_id, config["commandSubfolderSupport"]["default"])
    expanded = scanner.expand_commands_for_tool([resource], tool_id, supports_subfolders)
    return [{**item, "isDirectory": bool(item.get("isDirectory"))} for item in expanded]
