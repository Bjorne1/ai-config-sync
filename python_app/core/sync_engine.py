from pathlib import Path

from . import file_sync, linker


def _ensure_parent_dir(target_path: str) -> None:
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)


def validate_target(mode: str, source_path: str, target_path: str) -> bool:
    if mode == "copy":
        return file_sync.is_synced_copy(source_path, target_path)
    return linker.is_valid_symlink(target_path, source_path)


def describe_target_state(mode: str, source_path: str, target_path: str) -> dict[str, str]:
    if not Path(source_path).exists():
        return {"state": "source_missing", "message": "源文件不存在"}
    if validate_target(mode, source_path, target_path):
        return {"state": "healthy", "message": "已同步"}
    if not file_sync.has_path(target_path):
        return {"state": "missing", "message": "目标缺失"}
    message = "目标内容与源不一致" if mode == "copy" else "目标存在冲突或链接无效"
    return {"state": "conflict", "message": message}


def _sync_symlink(source_path: str, target_path: str, is_directory: bool) -> dict[str, object]:
    _ensure_parent_dir(target_path)
    created = linker.create_symlink(source_path, target_path, is_directory)
    if created.get("success") or not created.get("conflict"):
        return created
    removed = file_sync.remove_path(target_path)
    if not removed.get("success"):
        return {"success": False, "message": f"清理失败 - {removed['message']}"}
    return linker.create_symlink(source_path, target_path, is_directory)


def sync_entry(mode: str, source_path: str, target_path: str, is_directory: bool) -> dict[str, object]:
    if mode == "copy":
        _ensure_parent_dir(target_path)
        return file_sync.sync_copy(source_path, target_path)
    return _sync_symlink(source_path, target_path, is_directory)


def remove_target(target_path: str) -> dict[str, object]:
    return file_sync.remove_path(target_path)
