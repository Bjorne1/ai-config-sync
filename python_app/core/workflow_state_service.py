import json
import os
from pathlib import Path


WORKFLOW_STATE_VERSION = 1


def _default_state_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "ai-config-sync"
    return Path.home() / ".ai-config-sync"


DEFAULT_WORKFLOW_STATE_FILE = _default_state_dir() / "workflows.json"


def _normalize_target_entry(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    entry: dict[str, object] = {}
    for key in ("installedCommit", "installedVersion", "installedAt"):
        value = str(raw.get(key) or "").strip()
        if value:
            entry[key] = value
    return entry or None


def normalize_workflow_state(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, object]] = {}
    for workflow_id, payload in raw.items():
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            continue
        if not isinstance(payload, dict):
            continue
        raw_targets = payload.get("targets")
        if not isinstance(raw_targets, dict):
            continue
        targets: dict[str, object] = {}
        for target_key, target_entry in raw_targets.items():
            if not isinstance(target_key, str) or ":" not in target_key:
                continue
            normalized = _normalize_target_entry(target_entry)
            if normalized is not None:
                targets[target_key] = normalized
        if targets:
            result[workflow_id.strip()] = {"targets": targets}
    return result


def load_workflow_state(*, state_file: Path | None = None) -> dict[str, dict[str, object]]:
    resolved = state_file or DEFAULT_WORKFLOW_STATE_FILE
    if not resolved.exists():
        return {}
    parsed = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("workflows.json must be a JSON object.")
    version = parsed.get("version")
    if version != WORKFLOW_STATE_VERSION:
        raise ValueError(
            f"workflows.json version not supported: {version} (expected {WORKFLOW_STATE_VERSION})"
        )
    return normalize_workflow_state(parsed.get("workflows"))


def save_workflow_state(
    workflows: dict[str, object],
    *,
    state_file: Path | None = None,
) -> dict[str, dict[str, object]]:
    normalized = normalize_workflow_state(workflows)
    resolved = state_file or DEFAULT_WORKFLOW_STATE_FILE
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(
            {"version": WORKFLOW_STATE_VERSION, "workflows": normalized},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return normalized
