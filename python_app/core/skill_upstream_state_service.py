import json
from pathlib import Path


DEFAULT_SKILL_UPSTREAM_STATE_FILE = Path(__file__).resolve().parents[2] / "skill_sources.json"
SKILL_UPSTREAM_STATE_VERSION = 1


def create_default_skill_upstreams() -> dict[str, dict[str, object]]:
    return {}


def normalize_skill_upstreams_shape(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for name, payload in raw.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(payload, dict):
            continue
        url = str(payload.get("url") or "").strip()
        if not url:
            continue
        entry: dict[str, object] = {"url": url}
        installed_commit = str(payload.get("installedCommit") or "").strip()
        if installed_commit:
            entry["installedCommit"] = installed_commit
        normalized[name.strip()] = entry
    return normalized


def _resolve_state_file(state_file: Path | None) -> Path:
    return state_file or DEFAULT_SKILL_UPSTREAM_STATE_FILE


def load_skill_upstreams(*, state_file: Path | None = None) -> dict[str, dict[str, object]]:
    resolved = _resolve_state_file(state_file)
    if not resolved.exists():
        return create_default_skill_upstreams()
    parsed = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("skill_sources.json 必须是 JSON object。")
    version = parsed.get("version")
    if version != SKILL_UPSTREAM_STATE_VERSION:
        raise ValueError(
            f"skill_sources.json 版本不支持：{version}（期望 {SKILL_UPSTREAM_STATE_VERSION}）"
        )
    return normalize_skill_upstreams_shape(parsed.get("skills"))


def save_skill_upstreams(
    skills: dict[str, object],
    *,
    state_file: Path | None = None,
) -> dict[str, dict[str, object]]:
    normalized = normalize_skill_upstreams_shape(skills)
    resolved = _resolve_state_file(state_file)
    resolved.write_text(
        json.dumps(
            {"version": SKILL_UPSTREAM_STATE_VERSION, "skills": normalized},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return normalized

