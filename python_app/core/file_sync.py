import os
import shlex
import shutil
import subprocess
from pathlib import Path


def _copy_tree(source_path: str, target_path: str) -> None:
    shutil.copytree(source_path, target_path, copy_function=shutil.copy2)


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
        _copy_tree(source_path, target_path)
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


def _remove_directory(target: Path) -> None:
    # Some WSL UNC symlink entries can be mis-reported as directories.
    # Try unlink first to ensure links are removed before recursive delete.
    try:
        target.unlink()
        return
    except OSError:
        pass
    try:
        os.rmdir(target)
    except OSError:
        shutil.rmtree(target)


def _parse_wsl_unc_path(target_path: str) -> tuple[str, str] | None:
    normalized = target_path.replace("/", "\\")
    lowered = normalized.lower()
    prefixes = ("\\\\wsl.localhost\\", "\\\\wsl$\\")
    prefix = next((item for item in prefixes if lowered.startswith(item)), None)
    if prefix is None:
        return None
    remainder = normalized[len(prefix) :]
    parts = [part for part in remainder.split("\\") if part]
    if not parts:
        return None
    distro = parts[0]
    linux_path = "/" + "/".join(parts[1:]) if len(parts) > 1 else "/"
    return distro, linux_path


def _remove_wsl_unc_path(target_path: str) -> dict[str, object] | None:
    parsed = _parse_wsl_unc_path(target_path)
    if parsed is None:
        return None
    distro, linux_path = parsed
    quoted = shlex.quote(linux_path)
    command = (
        f"if [ -e {quoted} ] || [ -L {quoted} ]; then "
        f"rm -rf -- {quoted}; "
        f"if [ -e {quoted} ] || [ -L {quoted} ]; then echo __ERR__; exit 1; fi; "
        f"echo __OK__; "
        f"else echo __MISSING__; fi"
    )
    try:
        completed = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "sh", "-lc", command],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return {"success": False, "message": str(error)}
    output = (completed.stdout or "").strip()
    if completed.returncode != 0 or "__ERR__" in output:
        error_text = (completed.stderr or output or "WSL 删除失败").strip()
        return {"success": False, "message": error_text}
    if "__MISSING__" in output:
        return {"success": True, "skipped": True, "message": "目标不存在"}
    return {"success": True, "message": "删除成功"}


def remove_path(target_path: str) -> dict[str, object]:
    wsl_result = _remove_wsl_unc_path(target_path)
    if wsl_result is not None:
        return wsl_result
    if not has_path(target_path):
        return {"success": True, "skipped": True, "message": "目标不存在"}
    try:
        target = Path(target_path)
        if not os.path.exists(target_path) or os.path.islink(target_path):
            target.unlink()
        elif target.is_file():
            target.unlink()
        elif target.is_dir():
            _remove_directory(target)
        else:
            target.unlink()
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
