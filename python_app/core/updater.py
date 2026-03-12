import json
import subprocess


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    if not command:
        raise ValueError("command must not be empty")
    exe = command[0]
    if exe.lower() == "npm":
        return subprocess.run(["cmd.exe", "/c", *command], capture_output=True, text=True, check=True)
    return subprocess.run(command, capture_output=True, text=True, check=True)


def _run_wsl_capture(distro: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["wsl.exe", "-d", distro, "--", *command], capture_output=True, text=True, check=True)


def get_npm_version(package_name: str) -> str | None:
    try:
        completed = _run_capture(["npm", "list", "-g", package_name, "--json"])
    except (OSError, subprocess.CalledProcessError):
        return None
    try:
        data = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None
    return data.get("dependencies", {}).get(package_name, {}).get("version")


def get_npm_latest_version(package_name: str) -> str | None:
    try:
        completed = _run_capture(["npm", "view", package_name, "version", "--json"])
    except (OSError, subprocess.CalledProcessError):
        return None
    raw = (completed.stdout or "").strip()
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(decoded, str):
        return decoded
    return None


def get_wsl_npm_version(distro: str, package_name: str) -> str | None:
    try:
        completed = _run_wsl_capture(distro, ["npm", "list", "-g", package_name, "--json"])
    except (OSError, subprocess.CalledProcessError):
        return None
    try:
        data = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None
    return data.get("dependencies", {}).get(package_name, {}).get("version")


def update_npm_tool(package_name: str) -> bool:
    try:
        completed = subprocess.run(["cmd.exe", "/c", "npm", "install", "-g", f"{package_name}@latest"], text=True)
    except OSError:
        return False
    return completed.returncode == 0


def update_wsl_npm_tool(distro: str, package_name: str) -> bool:
    try:
        completed = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "npm", "install", "-g", f"{package_name}@latest"],
            text=True,
        )
    except OSError:
        return False
    return completed.returncode == 0


def update_command_tool(command: str) -> bool:
    try:
        completed = subprocess.run(command, shell=True, text=True)
    except OSError:
        return False
    return completed.returncode == 0


def update_wsl_command_tool(distro: str, command: str) -> bool:
    try:
        completed = subprocess.run(["wsl.exe", "-d", distro, "--", "sh", "-lc", command], text=True)
    except OSError:
        return False
    return completed.returncode == 0


def build_update_tool_statuses(
    tools: dict[str, dict[str, str]],
    wsl_distro: str | None = None,
) -> dict[str, dict[str, object]]:
    statuses: dict[str, dict[str, object]] = {}
    wsl_enabled = bool(wsl_distro)
    for name, config in tools.items():
        tool_type = config["type"]
        if tool_type != "npm":
            statuses[name] = {
                "type": tool_type,
                "wslEnabled": wsl_enabled,
                "currentWindows": None,
                "currentWsl": None,
                "latest": None,
            }
            continue
        package_name = config["package"]
        statuses[name] = {
            "type": tool_type,
            "wslEnabled": wsl_enabled,
            "currentWindows": get_npm_version(package_name),
            "currentWsl": get_wsl_npm_version(wsl_distro, package_name) if wsl_distro else None,
            "latest": get_npm_latest_version(package_name),
        }
    return statuses


def _set_update_success(success_windows: bool, success_wsl: bool | None) -> bool:
    if success_wsl is None:
        return bool(success_windows)
    return bool(success_windows and success_wsl)


def update_all_tools(
    tools: dict[str, dict[str, str]],
    wsl_distro: str | None = None,
    on_progress=None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    entries = list(tools.items())
    for index, (name, config) in enumerate(entries, start=1):
        result = {
            "name": name,
            "type": config["type"],
            "versionBefore": None,
            "versionAfter": None,
            "wslVersionBefore": None,
            "wslVersionAfter": None,
            "successWindows": False,
            "successWsl": None,
            "success": False,
        }
        if config["type"] == "npm":
            result["versionBefore"] = get_npm_version(config["package"])
            if wsl_distro:
                result["wslVersionBefore"] = get_wsl_npm_version(wsl_distro, config["package"])
        if on_progress:
            on_progress(name, index, len(entries), "updating")
        if config["type"] == "npm":
            result["successWindows"] = update_npm_tool(config["package"])
            result["versionAfter"] = get_npm_version(config["package"])
            if wsl_distro:
                result["successWsl"] = update_wsl_npm_tool(wsl_distro, config["package"])
                result["wslVersionAfter"] = get_wsl_npm_version(wsl_distro, config["package"])
        elif config["type"] in {"npx", "custom"}:
            result["successWindows"] = update_command_tool(config["command"])
            if wsl_distro:
                result["successWsl"] = update_wsl_command_tool(wsl_distro, config["command"])
        result["success"] = _set_update_success(result["successWindows"], result["successWsl"])
        results.append(result)
    return results
