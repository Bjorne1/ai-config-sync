import json
import re
from datetime import datetime
from pathlib import Path

from .tool_definitions import ENVIRONMENT_IDS, GLOBAL_RULE_TOOL_IDS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOBAL_RULE_STATE_FILE = PROJECT_ROOT / "global_rules.json"
DEFAULT_GLOBAL_RULE_PROFILE_DIR = PROJECT_ROOT / "agents" / "global-rules" / "profiles"
GLOBAL_RULE_STATE_VERSION = 1

_ILLEGAL_CHARS_RE = re.compile(r'[/\\:*?"<>|]')


def create_default_global_rule_assignments() -> dict[str, dict[str, str | None]]:
    return {
        environment_id: {tool_id: None for tool_id in GLOBAL_RULE_TOOL_IDS}
        for environment_id in ENVIRONMENT_IDS
    }


def create_default_global_rules() -> dict[str, object]:
    return {
        "profiles": [],
        "assignments": create_default_global_rule_assignments(),
    }


def _resolve_state_file(state_file: Path | None) -> Path:
    return state_file or DEFAULT_GLOBAL_RULE_STATE_FILE


def _resolve_profile_dir(profile_dir: Path | None) -> Path:
    return profile_dir or DEFAULT_GLOBAL_RULE_PROFILE_DIR


def _timestamp_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_profile_reference(value: object) -> str | None:
    profile_id = str(value or "").strip()
    return profile_id or None


def _sanitize_file_name(name: str) -> str:
    sanitized = _ILLEGAL_CHARS_RE.sub("_", name).strip(" .")
    return sanitized or "_unnamed"


def _build_profile_file_name(name: str) -> str:
    return f"{_sanitize_file_name(name)}.md"


def _normalize_profile_manifest(raw_profile: object) -> dict[str, str]:
    if not isinstance(raw_profile, dict):
        raise ValueError("规则版本必须是 object。")
    profile_id = str(raw_profile.get("id") or "").strip()
    name = str(raw_profile.get("name") or "").strip()
    description = str(raw_profile.get("description") or "").strip()
    updated_at = str(raw_profile.get("updatedAt") or "").strip()
    if not profile_id:
        raise ValueError("规则版本缺少 id。")
    if not name:
        raise ValueError(f"规则版本 {profile_id} 缺少名称。")
    return {
        "id": profile_id,
        "name": name,
        "description": description,
        "file": _build_profile_file_name(name),
        "updatedAt": updated_at,
    }


def _normalize_profile_payload(raw_profile: object) -> dict[str, str]:
    if not isinstance(raw_profile, dict):
        raise ValueError("规则版本必须是 object。")
    profile_id = str(raw_profile.get("id") or "").strip()
    name = str(raw_profile.get("name") or "").strip()
    description = str(raw_profile.get("description") or "").strip()
    content = str(raw_profile.get("content") or "")
    updated_at = str(raw_profile.get("updatedAt") or "").strip()
    if not profile_id:
        raise ValueError("规则版本缺少 id。")
    if not name:
        raise ValueError(f"规则版本 {profile_id} 缺少名称。")
    return {
        "id": profile_id,
        "name": name,
        "description": description,
        "file": _build_profile_file_name(name),
        "updatedAt": updated_at,
        "content": content,
    }


def _normalize_assignments(raw_assignments: object) -> dict[str, dict[str, str | None]]:
    assignments = raw_assignments if isinstance(raw_assignments, dict) else {}
    normalized: dict[str, dict[str, str | None]] = {}
    for environment_id in ENVIRONMENT_IDS:
        environment_assignments = assignments.get(environment_id)
        source = environment_assignments if isinstance(environment_assignments, dict) else {}
        normalized[environment_id] = {
            tool_id: _normalize_profile_reference(source.get(tool_id))
            for tool_id in GLOBAL_RULE_TOOL_IDS
        }
    return normalized


def _validate_assignments(
    assignments: dict[str, dict[str, str | None]],
    profile_ids: set[str],
) -> None:
    for environment_id in ENVIRONMENT_IDS:
        for tool_id in GLOBAL_RULE_TOOL_IDS:
            profile_id = assignments[environment_id][tool_id]
            if profile_id and profile_id not in profile_ids:
                raise ValueError(
                    f"目标 {environment_id}/{tool_id} 引用了不存在的规则版本：{profile_id}"
                )


def _load_manifest(
    state_file: Path,
) -> tuple[list[dict[str, str]], dict[str, dict[str, str | None]]]:
    parsed = json.loads(state_file.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("global_rules.json 必须是 JSON object。")
    version = parsed.get("version")
    if version != GLOBAL_RULE_STATE_VERSION:
        raise ValueError(
            f"global_rules.json 版本不支持：{version}（期望 {GLOBAL_RULE_STATE_VERSION}）"
        )
    raw_profiles = parsed.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("global_rules.json 中的 profiles 必须是数组。")
    profiles = [_normalize_profile_manifest(item) for item in raw_profiles]
    profile_ids = {profile["id"] for profile in profiles}
    if len(profile_ids) != len(profiles):
        raise ValueError("global_rules.json 中存在重复的规则版本 id。")
    assignments = _normalize_assignments(parsed.get("assignments"))
    _validate_assignments(assignments, profile_ids)
    return profiles, assignments


def load_global_rules(
    *,
    state_file: Path | None = None,
    profile_dir: Path | None = None,
) -> dict[str, object]:
    resolved_state_file = _resolve_state_file(state_file)
    resolved_profile_dir = _resolve_profile_dir(profile_dir)
    if not resolved_state_file.exists():
        resolved_profile_dir.mkdir(parents=True, exist_ok=True)
        return save_global_rules(
            create_default_global_rules(),
            state_file=resolved_state_file,
            profile_dir=resolved_profile_dir,
        )
    profiles, assignments = _load_manifest(resolved_state_file)
    loaded_profiles: list[dict[str, str]] = []
    for profile in profiles:
        file_path = resolved_profile_dir / profile["file"]
        if not file_path.exists():
            raise ValueError(f"缺少规则版本文件：{file_path}")
        loaded_profiles.append(
            {
                **profile,
                "content": file_path.read_text(encoding="utf-8"),
            }
        )
    resolved_profile_dir.mkdir(parents=True, exist_ok=True)
    return {"profiles": loaded_profiles, "assignments": assignments}


def save_global_rules(
    state: dict[str, object],
    *,
    state_file: Path | None = None,
    profile_dir: Path | None = None,
) -> dict[str, object]:
    resolved_state_file = _resolve_state_file(state_file)
    resolved_profile_dir = _resolve_profile_dir(profile_dir)
    resolved_profile_dir.mkdir(parents=True, exist_ok=True)
    existing_profiles: list[dict[str, str]] = []
    if resolved_state_file.exists():
        existing_profiles, _existing_assignments = _load_manifest(resolved_state_file)
    existing_by_id = {profile["id"]: profile for profile in existing_profiles}
    raw_profiles = state.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("profiles 必须是数组。")
    normalized_profiles = [_normalize_profile_payload(item) for item in raw_profiles]
    profile_ids = {profile["id"] for profile in normalized_profiles}
    if len(profile_ids) != len(normalized_profiles):
        raise ValueError("存在重复的规则版本 id。")
    profile_names = {profile["name"] for profile in normalized_profiles}
    if len(profile_names) != len(normalized_profiles):
        raise ValueError("存在重复的规则版本名称。")
    assignments = _normalize_assignments(state.get("assignments"))
    _validate_assignments(assignments, profile_ids)
    manifest_profiles: list[dict[str, str]] = []
    new_files: set[str] = set()
    for profile in normalized_profiles:
        existing = existing_by_id.get(profile["id"])
        existing_content = None
        if existing:
            existing_file = resolved_profile_dir / existing["file"]
            if existing_file.exists():
                existing_content = existing_file.read_text(encoding="utf-8")
        changed = (
            existing is None
            or existing["name"] != profile["name"]
            or existing["description"] != profile["description"]
            or existing_content != profile["content"]
        )
        updated_at = existing["updatedAt"] if existing and not changed else _timestamp_now()
        file_name = profile["file"]
        new_files.add(file_name)
        (resolved_profile_dir / file_name).write_text(profile["content"], encoding="utf-8")
        manifest_profiles.append(
            {
                "id": profile["id"],
                "name": profile["name"],
                "description": profile["description"],
                "file": file_name,
                "updatedAt": updated_at,
            }
        )
    old_files = {profile["file"] for profile in existing_profiles}
    removed_files = old_files - new_files
    for file_name in removed_files:
        file_path = resolved_profile_dir / file_name
        if file_path.exists():
            file_path.unlink()
    resolved_state_file.write_text(
        json.dumps(
            {
                "version": GLOBAL_RULE_STATE_VERSION,
                "profiles": manifest_profiles,
                "assignments": assignments,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return load_global_rules(state_file=resolved_state_file, profile_dir=resolved_profile_dir)
