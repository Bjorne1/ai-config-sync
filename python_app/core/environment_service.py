import os
import subprocess
import sys
from pathlib import Path

from .tool_definitions import TOOL_IDS, WINDOWS_HOME_TOKEN, WSL_HOME_TOKEN, build_root_map


def assert_windows_host(platform_name: str | None = None) -> None:
    current = platform_name or sys.platform
    if current != "win32":
        raise RuntimeError("This application only supports running on Windows.")


def resolve_windows_home(env: dict[str, str] | None = None, home_dir: str | None = None) -> str:
    environment = env or dict(os.environ)
    return environment.get("USERPROFILE") or home_dir or str(Path.home())


def expand_windows_path(input_path: str, env: dict[str, str] | None = None, home_dir: str | None = None) -> str:
    return input_path.replace(WINDOWS_HOME_TOKEN, resolve_windows_home(env, home_dir))


def expand_wsl_path(input_path: str, home_dir: str | None) -> str:
    if not home_dir:
        raise RuntimeError("WSL home directory is required to resolve WSL targets.")
    return input_path.replace(WSL_HOME_TOKEN, home_dir)


def _run_text_command(args: list[str]) -> str:
    completed = subprocess.run(args, capture_output=True, check=True, text=True)
    return completed.stdout


def list_wsl_distros(executor=_run_text_command) -> list[str]:
    output = executor(["wsl.exe", "-l", "-q"])
    return [line.replace("\x00", "").strip() for line in output.splitlines() if line.strip()]


def get_default_wsl_distro(executor=_run_text_command) -> str | None:
    output = executor(["wsl.exe", "-l", "-v"])
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    default_line = next((line for line in lines if line.startswith("*")), None)
    if not default_line:
        return None
    cleaned = default_line.removeprefix("*").strip()
    return cleaned.split()[0] if cleaned else None


def get_wsl_home_dir(distro: str, executor=_run_text_command) -> str:
    if not distro:
        raise RuntimeError("A WSL distro must be selected before resolving its home directory.")
    output = executor(["wsl.exe", "-d", distro, "sh", "-lc", 'printf %s "$HOME"'])
    return output.strip()


def linux_path_to_unc(distro: str, linux_path: str) -> str:
    sanitized = linux_path.lstrip("/").replace("/", "\\")
    return f"\\\\wsl.localhost\\{distro}\\{sanitized}"


def resolve_environment_targets(
    config: dict[str, object],
    env: dict[str, str] | None = None,
    home_dir: str | None = None,
    wsl_home: str | None = None,
    distro: str | None = None,
) -> dict[str, object]:
    environment = env or dict(os.environ)
    windows_home = resolve_windows_home(environment, home_dir)
    selected_distro = distro or config["environments"]["wsl"]["selectedDistro"]
    windows_targets = config["environments"]["windows"]["targets"]
    wsl_targets = config["environments"]["wsl"]["targets"]
    resolved_windows = {
        kind: {
            tool_id: expand_windows_path(windows_targets[kind][tool_id], environment, windows_home)
            for tool_id in TOOL_IDS
        }
        for kind in ("skills", "commands")
    }
    resolved_wsl = {}
    for kind in ("skills", "commands"):
        kind_targets: dict[str, str | None] = {}
        for tool_id in TOOL_IDS:
            resolved_path = expand_wsl_path(wsl_targets[kind][tool_id], wsl_home or WSL_HOME_TOKEN)
            kind_targets[tool_id] = (
                linux_path_to_unc(selected_distro, resolved_path) if selected_distro and wsl_home else None
            )
        resolved_wsl[kind] = kind_targets
    return {
        "windows": {
            "enabled": True,
            "targets": resolved_windows,
            "roots": build_root_map(windows_home, "windows"),
        },
        "wsl": {
            "enabled": bool(config["environments"]["wsl"]["enabled"] and selected_distro and wsl_home),
            "selectedDistro": selected_distro,
            "targets": resolved_wsl,
            "roots": build_root_map(linux_path_to_unc(selected_distro, wsl_home), "windows")
            if selected_distro and wsl_home
            else {tool_id: None for tool_id in TOOL_IDS},
        },
    }
