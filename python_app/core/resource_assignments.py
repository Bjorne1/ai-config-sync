from .tool_definitions import TOOL_IDS


def normalize_tool_list(items: object) -> list[str]:
    raw_items = items if isinstance(items, list) else []
    unique_items: list[str] = []
    for item in raw_items:
        if item in TOOL_IDS and item not in unique_items:
            unique_items.append(item)
    return unique_items


def normalize_environment_assignments(
    value: object,
    legacy_wsl_enabled: bool = False,
) -> dict[str, list[str]]:
    if isinstance(value, list):
        windows_tools = normalize_tool_list(value)
        wsl_tools = list(windows_tools) if legacy_wsl_enabled else []
    else:
        source = value if isinstance(value, dict) else {}
        windows_tools = normalize_tool_list(source.get("windows"))
        wsl_tools = normalize_tool_list(source.get("wsl"))
    normalized = {
        environment_id: tools
        for environment_id, tools in (("windows", windows_tools), ("wsl", wsl_tools))
        if tools
    }
    return normalized


def normalize_resource_map(
    raw_map: object,
    legacy_wsl_enabled: bool = False,
) -> dict[str, dict[str, list[str]]]:
    entries = raw_map.items() if isinstance(raw_map, dict) else []
    normalized: dict[str, dict[str, list[str]]] = {}
    for name, assignments in entries:
        if not isinstance(name, str) or not name.strip():
            continue
        environment_assignments = normalize_environment_assignments(assignments, legacy_wsl_enabled)
        if environment_assignments:
            normalized[name] = environment_assignments
    return normalized

