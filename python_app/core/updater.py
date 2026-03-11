import json
import subprocess


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=True)


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


def update_npm_tool(package_name: str) -> bool:
    try:
        completed = subprocess.run(["npm", "install", "-g", f"{package_name}@latest"], text=True)
    except OSError:
        return False
    return completed.returncode == 0


def update_command_tool(command: str) -> bool:
    try:
        completed = subprocess.run(command, shell=True, text=True)
    except OSError:
        return False
    return completed.returncode == 0


def update_all_tools(tools: dict[str, dict[str, str]], on_progress=None) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    entries = list(tools.items())
    for index, (name, config) in enumerate(entries, start=1):
        result = {
            "name": name,
            "type": config["type"],
            "versionBefore": None,
            "versionAfter": None,
            "success": False,
        }
        if config["type"] == "npm":
            result["versionBefore"] = get_npm_version(config["package"])
        if on_progress:
            on_progress(name, index, len(entries), "updating")
        if config["type"] == "npm":
            result["success"] = update_npm_tool(config["package"])
            result["versionAfter"] = get_npm_version(config["package"])
        elif config["type"] in {"npx", "custom"}:
            result["success"] = update_command_tool(config["command"])
        results.append(result)
    return results
