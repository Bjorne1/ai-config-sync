from pathlib import Path


def scan_skills(source_dir: str) -> list[dict[str, object]]:
    source_path = Path(source_dir)
    if not source_path.exists():
        return []
    skills: list[dict[str, object]] = []
    for item in sorted(source_path.iterdir(), key=lambda entry: entry.name.lower()):
        if item.name.startswith(".") or item.name == ".gitkeep":
            continue
        if item.is_file() or item.is_dir():
            skills.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "isDirectory": item.is_dir(),
                }
            )
    return skills


def scan_commands(source_dir: str) -> list[dict[str, object]]:
    source_path = Path(source_dir)
    if not source_path.exists():
        return []
    commands: list[dict[str, object]] = []
    for item in sorted(source_path.iterdir(), key=lambda entry: entry.name.lower()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.suffix == ".md":
            commands.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "isDirectory": False,
                    "parent": None,
                    "children": [],
                }
            )
            continue
        if not item.is_dir():
            continue
        children = [
            child.name
            for child in sorted(item.iterdir(), key=lambda entry: entry.name.lower())
            if child.is_file() and child.suffix == ".md" and not child.name.startswith(".")
        ]
        commands.append(
            {
                "name": item.name,
                "path": str(item),
                "isDirectory": True,
                "parent": None,
                "children": children,
            }
        )
    return commands


def flatten_command_name(folder_name: str, file_name: str) -> str:
    return f"{folder_name}-{file_name}"


def expand_commands_for_tool(
    commands: list[dict[str, object]],
    tool_id: str,
    subfolder_support: bool,
) -> list[dict[str, object]]:
    del tool_id
    expanded: list[dict[str, object]] = []
    for command in commands:
        if not command["isDirectory"]:
            expanded.append(
                {
                    "name": command["name"],
                    "sourcePath": command["path"],
                    "isFlattened": False,
                }
            )
            continue
        if subfolder_support:
            expanded.append(
                {
                    "name": command["name"],
                    "sourcePath": command["path"],
                    "isDirectory": True,
                    "isFlattened": False,
                }
            )
            continue
        for child in command["children"]:
            expanded.append(
                {
                    "name": flatten_command_name(command["name"], child),
                    "sourcePath": str(Path(command["path"]) / child),
                    "isFlattened": True,
                    "originalFolder": command["name"],
                }
            )
    return expanded
