import json
import os
import re
from copy import deepcopy
from pathlib import Path

from .tool_definitions import (
    CONFIG_VERSION,
    DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
    DEFAULT_SYNC_MODE,
    DEFAULT_UPDATE_TOOLS,
    TOOL_IDS,
    WINDOWS_HOME_TOKEN,
    WSL_HOME_TOKEN,
    build_target_map,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"
ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def _is_absolute_path(path_value: str) -> bool:
    return bool(ABSOLUTE_PATH_PATTERN.match(path_value))


def _should_create_source_dir(path_value: str | None) -> bool:
    if not path_value:
        return False
    if os.name == "nt" and path_value.startswith("/") and not WINDOWS_DRIVE_PATTERN.match(path_value):
        return False
    return True


def resolve_source_dir(config_path: str | None) -> str | None:
    if not config_path:
        return None
    if _is_absolute_path(config_path):
        return config_path
    return str((PROJECT_ROOT / config_path).resolve())


def normalize_tool_list(items: object) -> list[str]:
    raw_items = items if isinstance(items, list) else []
    unique_items: list[str] = []
    for item in raw_items:
        if item in TOOL_IDS and item not in unique_items:
            unique_items.append(item)
    return unique_items


def normalize_resource_map(raw_map: object) -> dict[str, list[str]]:
    entries = raw_map.items() if isinstance(raw_map, dict) else []
    normalized: dict[str, list[str]] = {}
    for name, tools in entries:
        tool_list = normalize_tool_list(tools)
        if tool_list:
            normalized[name] = tool_list
    return normalized


def normalize_command_subfolder_support(raw_support: object) -> dict[str, object]:
    support = raw_support if isinstance(raw_support, dict) else {}
    tools = support.get("tools") if isinstance(support.get("tools"), dict) else {}
    normalized_tools = {
        tool_id: bool(enabled)
        for tool_id, enabled in tools.items()
        if tool_id in TOOL_IDS
    }
    return {
        "default": support.get("default", DEFAULT_COMMAND_SUBFOLDER_SUPPORT["default"]),
        "tools": {
            **DEFAULT_COMMAND_SUBFOLDER_SUPPORT["tools"],
            **normalized_tools,
        },
    }


def normalize_update_tools(raw_tools: object) -> dict[str, dict[str, str]]:
    if not isinstance(raw_tools, dict):
        return deepcopy(DEFAULT_UPDATE_TOOLS)
    normalized: dict[str, dict[str, str]] = {}
    for name, value in raw_tools.items():
        if isinstance(value, dict) and value.get("type"):
            normalized[name] = deepcopy(value)
    return normalized


def create_default_config() -> dict[str, object]:
    return {
        "version": CONFIG_VERSION,
        "syncMode": DEFAULT_SYNC_MODE,
        "sourceDirs": {
            "skills": resolve_source_dir("skills"),
            "commands": resolve_source_dir("commands"),
        },
        "environments": {
            "windows": {
                "enabled": True,
                "targets": {
                    "skills": build_target_map(WINDOWS_HOME_TOKEN, "skills", "windows"),
                    "commands": build_target_map(WINDOWS_HOME_TOKEN, "commands", "windows"),
                },
            },
            "wsl": {
                "enabled": False,
                "selectedDistro": None,
                "targets": {
                    "skills": build_target_map(WSL_HOME_TOKEN, "skills", "posix"),
                    "commands": build_target_map(WSL_HOME_TOKEN, "commands", "posix"),
                },
            },
        },
        "resources": {"skills": {}, "commands": {}},
        "commandSubfolderSupport": normalize_command_subfolder_support(None),
        "updateTools": normalize_update_tools(None),
    }


def is_legacy_config(config: object) -> bool:
    if not isinstance(config, dict):
        return True
    return any(key not in config for key in ("version", "sourceDirs", "environments", "resources"))


def merge_targets(default_targets: dict[str, str], overrides: object) -> dict[str, str]:
    source = overrides if isinstance(overrides, dict) else {}
    return {tool_id: source.get(tool_id) or default_targets[tool_id] for tool_id in TOOL_IDS}


def migrate_legacy_config(legacy_config: object) -> dict[str, object]:
    defaults = create_default_config()
    legacy = legacy_config if isinstance(legacy_config, dict) else {}
    return {
        "version": CONFIG_VERSION,
        "syncMode": legacy.get("syncMode") or DEFAULT_SYNC_MODE,
        "sourceDirs": {
            "skills": resolve_source_dir(legacy.get("sourceDir") or defaults["sourceDirs"]["skills"]),
            "commands": resolve_source_dir(
                legacy.get("commandsSourceDir") or defaults["sourceDirs"]["commands"]
            ),
        },
        "environments": {
            "windows": {
                "enabled": True,
                "targets": {
                    "skills": merge_targets(defaults["environments"]["windows"]["targets"]["skills"], legacy.get("targets")),
                    "commands": merge_targets(
                        defaults["environments"]["windows"]["targets"]["commands"],
                        legacy.get("commandTargets"),
                    ),
                },
            },
            "wsl": {
                "enabled": bool(legacy.get("wslEnabled")),
                "selectedDistro": legacy.get("wslDistro"),
                "targets": {
                    "skills": merge_targets(
                        defaults["environments"]["wsl"]["targets"]["skills"],
                        legacy.get("wslTargets", {}).get("skills"),
                    ),
                    "commands": merge_targets(
                        defaults["environments"]["wsl"]["targets"]["commands"],
                        legacy.get("wslTargets", {}).get("commands"),
                    ),
                },
            },
        },
        "resources": {
            "skills": normalize_resource_map(legacy.get("skills")),
            "commands": normalize_resource_map(legacy.get("commands")),
        },
        "commandSubfolderSupport": normalize_command_subfolder_support(
            legacy.get("commandSubfolderSupport")
        ),
        "updateTools": normalize_update_tools(legacy.get("updateTools")),
    }


def normalize_config_shape(raw_config: object) -> dict[str, object]:
    defaults = create_default_config()
    config = raw_config if isinstance(raw_config, dict) else {}
    environments = config.get("environments") if isinstance(config.get("environments"), dict) else {}
    windows = environments.get("windows") if isinstance(environments.get("windows"), dict) else {}
    wsl = environments.get("wsl") if isinstance(environments.get("wsl"), dict) else {}
    return {
        "version": CONFIG_VERSION,
        "syncMode": "copy" if config.get("syncMode") == "copy" else DEFAULT_SYNC_MODE,
        "sourceDirs": {
            "skills": resolve_source_dir(config.get("sourceDirs", {}).get("skills") or defaults["sourceDirs"]["skills"]),
            "commands": resolve_source_dir(
                config.get("sourceDirs", {}).get("commands") or defaults["sourceDirs"]["commands"]
            ),
        },
        "environments": {
            "windows": {
                "enabled": True,
                "targets": {
                    "skills": merge_targets(defaults["environments"]["windows"]["targets"]["skills"], windows.get("targets", {}).get("skills")),
                    "commands": merge_targets(
                        defaults["environments"]["windows"]["targets"]["commands"],
                        windows.get("targets", {}).get("commands"),
                    ),
                },
            },
            "wsl": {
                "enabled": bool(wsl.get("enabled")),
                "selectedDistro": wsl.get("selectedDistro"),
                "targets": {
                    "skills": merge_targets(defaults["environments"]["wsl"]["targets"]["skills"], wsl.get("targets", {}).get("skills")),
                    "commands": merge_targets(
                        defaults["environments"]["wsl"]["targets"]["commands"],
                        wsl.get("targets", {}).get("commands"),
                    ),
                },
            },
        },
        "resources": {
            "skills": normalize_resource_map(config.get("resources", {}).get("skills")),
            "commands": normalize_resource_map(config.get("resources", {}).get("commands")),
        },
        "commandSubfolderSupport": normalize_command_subfolder_support(
            config.get("commandSubfolderSupport")
        ),
        "updateTools": normalize_update_tools(config.get("updateTools")),
    }


def parse_config_file(raw_content: str) -> tuple[dict[str, object], bool]:
    parsed = json.loads(raw_content)
    if is_legacy_config(parsed):
        return migrate_legacy_config(parsed), True
    return normalize_config_shape(parsed), False


def ensure_config_directories(config: dict[str, object]) -> None:
    source_dirs = config.get("sourceDirs", {})
    for dir_path in (source_dirs.get("skills"), source_dirs.get("commands")):
        if _should_create_source_dir(dir_path):
            Path(dir_path).mkdir(parents=True, exist_ok=True)


def save_config(config: dict[str, object]) -> dict[str, object]:
    normalized = normalize_config_shape(config)
    CONFIG_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return normalized


def load_config() -> dict[str, object]:
    if not CONFIG_FILE.exists():
        created = create_default_config()
        ensure_config_directories(created)
        return save_config(created)
    raw_content = CONFIG_FILE.read_text(encoding="utf-8")
    config, migrated = parse_config_file(raw_content)
    ensure_config_directories(config)
    if migrated or raw_content.strip() != json.dumps(config, indent=2, ensure_ascii=False):
        return save_config(config)
    return config
