import os
import shutil
from pathlib import Path


def _get_lstat(target_path: str):
    try:
        return os.lstat(target_path)
    except FileNotFoundError:
        return None


def has_path(target_path: str) -> bool:
    return os.path.lexists(target_path)


def _is_file_copy_synced(source_path: str, target_path: str) -> bool:
    target_stat = _get_lstat(target_path)
    if not target_stat or os.path.islink(target_path) or not Path(target_path).is_file():
        return False
    if Path(source_path).stat().st_size != target_stat.st_size:
        return False
    return Path(source_path).read_bytes() == Path(target_path).read_bytes()


def _is_directory_copy_synced(source_path: str, target_path: str) -> bool:
    target = Path(target_path)
    if not has_path(target_path) or target.is_symlink() or not target.is_dir():
        return False
    source_entries = sorted(item.name for item in Path(source_path).iterdir())
    target_entries = sorted(item.name for item in target.iterdir())
    if source_entries != target_entries:
        return False
    return all(
        is_synced_copy(str(Path(source_path) / entry), str(target / entry))
        for entry in source_entries
    )


def is_synced_copy(source_path: str, target_path: str) -> bool:
    source = Path(source_path)
    if not source.exists():
        return False
    if source.is_dir():
        return _is_directory_copy_synced(source_path, target_path)
    return _is_file_copy_synced(source_path, target_path)


def _copy_path(source_path: str, target_path: str) -> None:
    source = Path(source_path)
    if source.is_dir():
        shutil.copytree(source_path, target_path)
        return
    shutil.copy2(source_path, target_path)


def create_copy(source_path: str, target_path: str) -> dict[str, object]:
    source = Path(source_path)
    if not source.exists():
        return {"success": False, "message": "源文件不存在"}
    if has_path(target_path):
        if is_synced_copy(source_path, target_path):
            return {"success": True, "skipped": True, "message": "已存在最新副本"}
        return {"success": False, "conflict": True, "message": "目标位置已存在文件或目录"}
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        _copy_path(source_path, target_path)
    except OSError as error:
        return {"success": False, "message": str(error)}
    return {"success": True, "message": "复制成功"}


def remove_path(target_path: str) -> dict[str, object]:
    if not has_path(target_path):
        return {"success": True, "skipped": True, "message": "目标不存在"}
    try:
        target = Path(target_path)
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target_path)
    except OSError as error:
        return {"success": False, "message": str(error)}
    return {"success": True, "message": "删除成功"}


def sync_copy(source_path: str, target_path: str) -> dict[str, object]:
    copy_result = create_copy(source_path, target_path)
    if copy_result.get("success") or not copy_result.get("conflict"):
        return copy_result
    remove_result = remove_path(target_path)
    if not remove_result.get("success"):
        return {"success": False, "message": f"清理失败 - {remove_result['message']}"}
    retry_result = create_copy(source_path, target_path)
    if retry_result.get("success"):
        return {"success": True, "message": "同步成功"}
    return retry_result
