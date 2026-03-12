import os
from pathlib import Path

from . import file_sync, linker


def _ensure_parent_dir(target_path: str) -> None:
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)


def validate_target(mode: str, source_path: str, target_path: str) -> bool:
    if mode == "copy":
        return file_sync.is_synced_copy(source_path, target_path)
    return linker.is_valid_symlink(target_path, source_path)


def _latest_mtime_ns(path: Path) -> int:
    if path.is_dir():
        latest = path.stat(follow_symlinks=False).st_mtime_ns
        for directory, _directories, files in os.walk(path):
            for filename in files:
                candidate = Path(directory) / filename
                latest = max(latest, candidate.stat(follow_symlinks=False).st_mtime_ns)
        return latest
    return path.stat(follow_symlinks=False).st_mtime_ns


def _describe_copy_mismatch(source_path: str, target_path: str) -> dict[str, str]:
    source = Path(source_path)
    target = Path(target_path)
    if target.is_symlink():
        return {"state": "conflict", "message": "目标是软链接，无法作为副本升级"}
    if source.is_dir() != target.is_dir():
        return {"state": "conflict", "message": "目标类型与源不一致"}
    source_mtime = _latest_mtime_ns(source)
    target_mtime = _latest_mtime_ns(target)
    if source_mtime > target_mtime:
        return {"state": "outdated", "message": "源更新于目标，可升级"}
    if source_mtime < target_mtime:
        return {"state": "ahead", "message": "目标更新于源，存在覆盖风险"}
    return {"state": "conflict", "message": "目标内容与源不一致"}


def describe_target_state(mode: str, source_path: str, target_path: str) -> dict[str, str]:
    if not Path(source_path).exists():
        return {"state": "source_missing", "message": "源文件不存在"}
    if validate_target(mode, source_path, target_path):
        return {"state": "healthy", "message": "已同步"}
    if not file_sync.has_path(target_path):
        return {"state": "missing", "message": "目标缺失"}
    if mode == "copy":
        return _describe_copy_mismatch(source_path, target_path)
    return {"state": "conflict", "message": "目标存在冲突或链接无效"}


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
