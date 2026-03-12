from pathlib import Path


def get_cleanup_targets(kind: str, resource_name: str, entry: dict[str, object]) -> list[str]:
    targets = entry.get("targets") if isinstance(entry, dict) else None
    target_list = targets if isinstance(targets, list) else []
    target_path = entry.get("targetPath") if isinstance(entry, dict) else None
    if target_list and kind != "commands":
        return target_list
    if not target_path:
        return target_list
    if kind != "commands":
        return [str(Path(target_path) / resource_name)]
    direct_path = str(Path(target_path) / resource_name)
    flattened: list[str] = []
    target_dir = Path(target_path)
    if target_dir.exists():
        flattened = [
            str(target_dir / item.name)
            for item in target_dir.iterdir()
            if item.name.startswith(f"{resource_name}-")
        ]
    return list(dict.fromkeys([*target_list, direct_path, *flattened]))

