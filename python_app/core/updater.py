import json
import re
import shlex
import subprocess

from .process_utils import hidden_subprocess_kwargs


SEMVER_STABLE_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SEMVER_CORE_PATTERN = re.compile(r"^(\d+\.\d+\.\d+)")


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    if not command:
        raise ValueError("command must not be empty")
    exe = command[0]
    if exe.lower() == "npm":
        return subprocess.run(
            ["cmd.exe", "/c", *command],
            capture_output=True,
            text=True,
            check=True,
            **hidden_subprocess_kwargs(),
        )
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        **hidden_subprocess_kwargs(),
    )


def _run_wsl_capture(distro: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    shell_command = shlex.join(command)
    return subprocess.run(
        ["wsl.exe", "-d", distro, "--", "bash", "-ic", shell_command],
        capture_output=True,
        text=True,
        check=True,
        **hidden_subprocess_kwargs(),
    )


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


def get_npm_recent_versions(package_name: str, limit: int = 10) -> list[str]:
    if limit <= 0:
        return []
    try:
        completed = _run_capture(["npm", "view", package_name, "versions", "--json"])
    except (OSError, subprocess.CalledProcessError):
        return []
    raw = (completed.stdout or "").strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(decoded, str):
        raw_versions = [decoded.strip()] if decoded.strip() else []
    elif isinstance(decoded, list):
        raw_versions = [str(item).strip() for item in decoded if str(item).strip()]
    else:
        raw_versions = []
    if not raw_versions:
        return []
    unique_versions = list(dict.fromkeys(raw_versions))
    stable_versions = [version for version in unique_versions if SEMVER_STABLE_PATTERN.match(version)]
    if stable_versions:
        return list(reversed(stable_versions[-limit:]))
    selected: list[str] = []
    seen_cores: set[str] = set()
    for version in reversed(unique_versions):
        match = SEMVER_CORE_PATTERN.match(version)
        core = match.group(1) if match else version
        if core in seen_cores:
            continue
        seen_cores.add(core)
        selected.append(version)
        if len(selected) >= limit:
            break
    return selected


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


def update_npm_tool(package_name: str, version: str = "latest") -> bool:
    resolved_version = str(version or "latest").strip() or "latest"
    try:
        completed = subprocess.run(
            ["cmd.exe", "/c", "npm", "install", "-g", f"{package_name}@{resolved_version}"],
            text=True,
            **hidden_subprocess_kwargs(),
        )
    except OSError:
        return False
    return completed.returncode == 0


def update_wsl_npm_tool(distro: str, package_name: str, version: str = "latest") -> bool:
    resolved_version = str(version or "latest").strip() or "latest"
    shell_command = shlex.join(["npm", "install", "-g", f"{package_name}@{resolved_version}"])
    try:
        completed = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "bash", "-ic", shell_command],
            text=True,
            **hidden_subprocess_kwargs(),
        )
    except OSError:
        return False
    return completed.returncode == 0


def update_command_tool(command: str) -> bool:
    try:
        completed = subprocess.run(command, shell=True, text=True, **hidden_subprocess_kwargs())
    except OSError:
        return False
    return completed.returncode == 0


def update_wsl_command_tool(distro: str, command: str) -> bool:
    try:
        completed = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "bash", "-ic", command],
            text=True,
            **hidden_subprocess_kwargs(),
        )
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
                "recentVersions": [],
            }
            continue
        package_name = config["package"]
        latest_version = get_npm_latest_version(package_name)
        recent_versions = get_npm_recent_versions(package_name, limit=10)
        if latest_version and latest_version not in recent_versions:
            recent_versions = [latest_version, *recent_versions][:10]
        statuses[name] = {
            "type": tool_type,
            "wslEnabled": wsl_enabled,
            "currentWindows": get_npm_version(package_name),
            "currentWsl": get_wsl_npm_version(wsl_distro, package_name) if wsl_distro else None,
            "latest": latest_version,
            "recentVersions": recent_versions,
        }
    return statuses


def _set_update_success(success_windows: bool, success_wsl: bool | None) -> bool:
    if success_wsl is None:
        return bool(success_windows)
    return bool(success_windows and success_wsl)


def update_all_tools(
    tools: dict[str, dict[str, str]],
    wsl_distro: str | None = None,
    target_versions: dict[str, str] | None = None,
    on_progress=None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    entries = list(tools.items())
    for index, (name, config) in enumerate(entries, start=1):
        result = {
            "name": name,
            "type": config["type"],
            "targetVersion": None,
            "versionBefore": None,
            "versionAfter": None,
            "wslVersionBefore": None,
            "wslVersionAfter": None,
            "successWindows": False,
            "successWsl": None,
            "success": False,
        }
        target_version = "latest"
        if config["type"] == "npm" and isinstance(target_versions, dict):
            target_version = str(target_versions.get(name) or "").strip() or "latest"
            result["targetVersion"] = target_version
        if config["type"] == "npm":
            result["versionBefore"] = get_npm_version(config["package"])
            if wsl_distro:
                result["wslVersionBefore"] = get_wsl_npm_version(wsl_distro, config["package"])
        if on_progress:
            on_progress(name, index, len(entries), "updating")
        if config["type"] == "npm":
            result["successWindows"] = update_npm_tool(config["package"], target_version)
            result["versionAfter"] = get_npm_version(config["package"])
            if wsl_distro:
                result["successWsl"] = update_wsl_npm_tool(wsl_distro, config["package"], target_version)
                result["wslVersionAfter"] = get_wsl_npm_version(wsl_distro, config["package"])
        elif config["type"] in {"npx", "custom"}:
            result["successWindows"] = update_command_tool(config["command"])
            if wsl_distro:
                result["successWsl"] = update_wsl_command_tool(wsl_distro, config["command"])
        result["success"] = _set_update_success(result["successWindows"], result["successWsl"])
        results.append(result)
    return results
