from pathlib import Path

from .markdown_description import read_description_from_markdown, read_description_from_skill_folder

def scan_skills(source_dir: str) -> list[dict[str, object]]:
    source_path = Path(source_dir)
    if not source_path.exists():
        return []
    skills: list[dict[str, object]] = []
    for item in sorted(source_path.iterdir(), key=lambda entry: entry.name.lower()):
        if item.name.startswith(".") or item.name == ".gitkeep":
            continue
        if item.is_file() or item.is_dir():
            meta = read_description_from_skill_folder(item)
            skills.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "isDirectory": item.is_dir(),
                    "description": meta.description if meta else "",
                    "descriptionSource": meta.source if meta else "",
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
            meta = read_description_from_markdown(item)
            commands.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "isDirectory": False,
                    "parent": None,
                    "children": [],
                    "description": meta.description if meta else "",
                    "descriptionSource": meta.source if meta else "",
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
        summary = f"包含 {len(children)} 个子命令" if children else ""
        commands.append(
            {
                "name": item.name,
                "path": str(item),
                "isDirectory": True,
                "parent": None,
                "children": children,
                "description": summary,
                "descriptionSource": "derived" if summary else "",
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
