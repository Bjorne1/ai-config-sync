import json
import os
from pathlib import Path

from .resource_assignments import normalize_resource_map

RESOURCE_STATE_VERSION = 1


def _default_state_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "ai-config-sync"
    return Path.home() / ".ai-config-sync"


DEFAULT_RESOURCE_STATE_FILE = _default_state_dir() / "resources.json"


def create_default_resources() -> dict[str, dict[str, dict[str, list[str]]]]:
    return {"skills": {}, "commands": {}}


def normalize_resources_shape(raw_resources: object) -> dict[str, dict[str, dict[str, list[str]]]]:
    source = raw_resources if isinstance(raw_resources, dict) else {}
    return {
        "skills": normalize_resource_map(source.get("skills")),
        "commands": normalize_resource_map(source.get("commands")),
    }


def _resolve_state_file(state_file: Path | None) -> Path:
    return state_file or DEFAULT_RESOURCE_STATE_FILE


def load_resources(*, state_file: Path | None = None) -> dict[str, dict[str, dict[str, list[str]]]]:
    resolved = _resolve_state_file(state_file)
    if not resolved.exists():
        return create_default_resources()
    parsed = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("resources.json 必须是 JSON object。")
    version = parsed.get("version")
    if version != RESOURCE_STATE_VERSION:
        raise ValueError(f"resources.json 版本不支持：{version}（期望 {RESOURCE_STATE_VERSION}）")
    return normalize_resources_shape(parsed.get("resources"))


def save_resources(
    resources: dict[str, object],
    *,
    state_file: Path | None = None,
) -> dict[str, dict[str, dict[str, list[str]]]]:
    normalized = normalize_resources_shape(resources)
    resolved = _resolve_state_file(state_file)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(
            {"version": RESOURCE_STATE_VERSION, "resources": normalized},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return normalized
