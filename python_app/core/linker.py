import os
from pathlib import Path


def is_valid_symlink(target_path: str, expected_source: str) -> bool:
    if not os.path.lexists(target_path):
        return False
    target = Path(target_path)
    if not target.is_symlink():
        return False
    try:
        link_target = os.readlink(target_path)
    except OSError:
        return False
    resolved_target = (target.parent / link_target).resolve()
    return resolved_target == Path(expected_source).resolve()


def create_symlink(source_path: str, target_path: str, is_directory: bool) -> dict[str, object]:
    source = Path(source_path)
    if not source.exists():
        return {"success": False, "message": "源文件不存在"}
    if os.path.lexists(target_path):
        if is_valid_symlink(target_path, source_path):
            return {"success": True, "skipped": True, "message": "已存在有效链接"}
        return {"success": False, "conflict": True, "message": "目标位置已存在文件或目录"}
    try:
        os.symlink(source_path, target_path, target_is_directory=is_directory)
    except PermissionError as error:
        return {"success": False, "permission": True, "message": str(error) or "权限不足"}
    except OSError as error:
        return {"success": False, "message": str(error)}
    return {"success": True, "message": "创建成功"}


def remove_symlink(target_path: str) -> dict[str, object]:
    if not os.path.lexists(target_path):
        return {"success": True, "skipped": True, "message": "链接不存在"}
    if not Path(target_path).is_symlink():
        return {"success": False, "message": "目标不是软链接，拒绝删除"}
    try:
        Path(target_path).unlink()
    except OSError as error:
        return {"success": False, "message": str(error)}
    return {"success": True, "message": "删除成功"}
