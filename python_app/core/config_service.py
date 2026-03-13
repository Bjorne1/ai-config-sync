import json
import os
import re
from copy import deepcopy
from pathlib import Path

from .resource_assignments import normalize_resource_map
from .resource_state_service import load_resources, save_resources
from .tool_definitions import (
    CONFIG_VERSION,
    DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
    DEFAULT_SYNC_MODE,
    DEFAULT_UPDATE_TOOLS,
    TOOL_IDS,
    UPDATE_TOOL_TYPES,
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


def _extract_embedded_resources(raw_config: object) -> dict[str, object] | None:
    if not isinstance(raw_config, dict):
        return None
    resources = raw_config.get("resources")
    return resources if isinstance(resources, dict) else None


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
        if not isinstance(value, dict):
            continue
        tool_type = value.get("type")
        if tool_type not in UPDATE_TOOL_TYPES:
            continue
        if tool_type == "npm":
            package = str(value.get("package") or "").strip()
            if package:
                normalized[name] = {"type": tool_type, "package": package}
            continue
        command = str(value.get("command") or "").strip()
        if command:
            normalized[name] = {"type": tool_type, "command": command}
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
                "selectedDistro": None,
                "targets": {
                    "skills": build_target_map(WSL_HOME_TOKEN, "skills", "posix"),
                    "commands": build_target_map(WSL_HOME_TOKEN, "commands", "posix"),
                },
            },
        },
        "commandSubfolderSupport": normalize_command_subfolder_support(None),
        "updateTools": normalize_update_tools(None),
    }


def is_legacy_config(config: object) -> bool:
    if not isinstance(config, dict):
        return True
    return any(key not in config for key in ("version", "sourceDirs", "environments"))


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
            "skills": normalize_resource_map(
                legacy.get("skills"),
                legacy_wsl_enabled=bool(legacy.get("wslEnabled")),
            ),
            "commands": normalize_resource_map(
                legacy.get("commands"),
                legacy_wsl_enabled=bool(legacy.get("wslEnabled")),
            ),
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
            "skills": normalize_resource_map(
                config.get("resources", {}).get("skills"),
                legacy_wsl_enabled=bool(wsl.get("enabled")),
            ),
            "commands": normalize_resource_map(
                config.get("resources", {}).get("commands"),
                legacy_wsl_enabled=bool(wsl.get("enabled")),
            ),
        },
        "commandSubfolderSupport": normalize_command_subfolder_support(
            config.get("commandSubfolderSupport")
        ),
        "updateTools": normalize_update_tools(config.get("updateTools")),
    }


def _build_config_file_payload(config: dict[str, object]) -> dict[str, object]:
    payload = {key: value for key, value in config.items() if key != "resources"}
    payload["version"] = CONFIG_VERSION
    return payload


def parse_config_file(raw_content: str) -> tuple[dict[str, object], bool, dict[str, object] | None]:
    parsed = json.loads(raw_content)
    embedded_resources = _extract_embedded_resources(parsed)
    if is_legacy_config(parsed):
        migrated = migrate_legacy_config(parsed)
        return migrated, True, migrated.get("resources") if isinstance(migrated.get("resources"), dict) else None
    normalized = normalize_config_shape(parsed)
    migrated = parsed.get("version") != CONFIG_VERSION or embedded_resources is not None
    return normalized, migrated, embedded_resources


def ensure_config_directories(config: dict[str, object]) -> None:
    source_dirs = config.get("sourceDirs", {})
    for dir_path in (source_dirs.get("skills"), source_dirs.get("commands")):
        if _should_create_source_dir(dir_path):
            Path(dir_path).mkdir(parents=True, exist_ok=True)


def save_config(config: dict[str, object]) -> dict[str, object]:
    normalized = normalize_config_shape(config)
    normalized_resources = save_resources(
        normalized.get("resources", {}),
        state_file=PROJECT_ROOT / "resources.json",
    )
    CONFIG_FILE.write_text(
        json.dumps(_build_config_file_payload(normalized), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {**normalized, "resources": normalized_resources}


def load_config() -> dict[str, object]:
    if not CONFIG_FILE.exists():
        created = create_default_config()
        ensure_config_directories(created)
        return save_config(created)
    raw_content = CONFIG_FILE.read_text(encoding="utf-8")
    config, migrated, embedded_resources = parse_config_file(raw_content)
    runtime_resources = config.get("resources", {"skills": {}, "commands": {}})
    if embedded_resources is None:
        runtime_resources = load_resources(state_file=PROJECT_ROOT / "resources.json")
        config = {**config, "resources": runtime_resources}
    ensure_config_directories(config)
    normalized_file = json.dumps(_build_config_file_payload(config), indent=2, ensure_ascii=False)
    if migrated or raw_content.strip() != normalized_file:
        return save_config(config)
    if embedded_resources is not None:
        save_resources(runtime_resources, state_file=PROJECT_ROOT / "resources.json")
        return {**config, "resources": runtime_resources}
    return {**config, "resources": runtime_resources}
