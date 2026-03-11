from pathlib import Path

from .environment_service import (
    get_default_wsl_distro,
    get_wsl_home_dir,
    list_wsl_distros,
    resolve_environment_targets,
)
from .tool_definitions import WINDOWS_HOME_TOKEN, WSL_HOME_TOKEN


def _is_tokenized_target(target_path: str) -> bool:
    return WINDOWS_HOME_TOKEN in target_path or WSL_HOME_TOKEN in target_path


def _is_tool_available(root_path: str | None, raw_target_path: str) -> bool:
    if not root_path:
        return False
    if not _is_tokenized_target(raw_target_path):
        return True
    return Path(root_path).exists()


def build_wsl_runtime(config: dict[str, object], deps: dict[str, object] | None = None) -> dict[str, object]:
    api = {
        "get_default_wsl_distro": get_default_wsl_distro,
        "get_wsl_home_dir": get_wsl_home_dir,
        "list_wsl_distros": list_wsl_distros,
        **(deps or {}),
    }
    wsl_config = config["environments"]["wsl"]
    try:
        distros = api["list_wsl_distros"]()
        default_distro = api["get_default_wsl_distro"]()
        selected_distro = wsl_config["selectedDistro"] or default_distro
        home_dir = api["get_wsl_home_dir"](selected_distro) if selected_distro else None
    except Exception as error:  # noqa: BLE001
        return {
            "available": False,
            "distros": [],
            "selectedDistro": wsl_config["selectedDistro"],
            "homeDir": None,
            "error": str(error),
        }
    if not distros:
        error = "未发现 WSL 发行版"
    elif not selected_distro:
        error = "未能解析默认 WSL 发行版"
    elif not home_dir:
        error = "未能解析 WSL 主目录"
    else:
        error = None
    return {
        "available": bool(selected_distro and home_dir),
        "distros": distros,
        "selectedDistro": selected_distro,
        "homeDir": home_dir,
        "error": error,
    }


def build_environment_list(config: dict[str, object], deps: dict[str, object] | None = None) -> dict[str, object]:
    api = {"resolve_environment_targets": resolve_environment_targets, **(deps or {})}
    wsl_runtime = build_wsl_runtime(config, deps)
    resolved = api["resolve_environment_targets"](
        config,
        distro=wsl_runtime["selectedDistro"],
        wsl_home=wsl_runtime["homeDir"],
    )
    return {
        "windows": {
            "id": "windows",
            "enabled": True,
            "label": "Windows",
            "rawTargets": config["environments"]["windows"]["targets"],
            "roots": resolved["windows"]["roots"],
            "targets": resolved["windows"]["targets"],
            "error": None,
        },
        "wsl": {
            "id": "wsl",
            "enabled": bool(wsl_runtime["selectedDistro"] or wsl_runtime["distros"]),
            "label": f"WSL · {wsl_runtime['selectedDistro']}" if wsl_runtime["selectedDistro"] else "WSL",
            "rawTargets": config["environments"]["wsl"]["targets"],
            "roots": resolved["wsl"]["roots"],
            "targets": resolved["wsl"]["targets"],
            "error": wsl_runtime["error"],
            "meta": wsl_runtime,
        },
    }


def build_availability(environment: dict[str, object], kind: str, tool_id: str) -> dict[str, object]:
    if environment["id"] == "wsl" and environment["error"]:
        return {"available": False, "state": "environment_error", "message": environment["error"]}
    if environment["id"] == "wsl" and not environment["meta"]["available"]:
        return {
            "available": False,
            "state": "environment_error",
            "message": "未能解析 WSL 发行版或主目录",
        }
    raw_target = environment["rawTargets"][kind][tool_id]
    root_path = environment["roots"][tool_id]
    if not _is_tool_available(root_path, raw_target):
        return {"available": False, "state": "tool_unavailable", "message": "工具目录不存在"}
    return {"available": True}
