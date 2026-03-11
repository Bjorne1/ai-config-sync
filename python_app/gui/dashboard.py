import json

STATE_LABELS = {
    "healthy": "已同步",
    "missing": "目标缺失",
    "conflict": "存在冲突",
    "source_missing": "源不存在",
    "tool_unavailable": "工具未安装",
    "environment_error": "环境异常",
    "partial": "部分完成",
    "idle": "未分配",
}
STATE_PRIORITY = {
    "conflict": 0,
    "source_missing": 1,
    "environment_error": 2,
    "tool_unavailable": 3,
    "missing": 4,
    "partial": 5,
    "healthy": 6,
    "idle": 7,
}


def serialize(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _children_count(entry: dict[str, object] | None) -> int:
    if not entry:
        return 0
    children = entry.get("children")
    return len(children) if isinstance(children, list) else 0


def summarize_entries(entries: list[dict[str, object]], configured_tools: list[str]) -> tuple[str, str]:
    if not configured_tools:
        return "idle", STATE_LABELS["idle"]
    if not entries:
        return "partial", "已分配但尚无状态明细"
    ordered = sorted(entries, key=lambda entry: STATE_PRIORITY[entry["state"]])
    summary = ordered[0]
    return summary["state"], summary.get("message") or STATE_LABELS[summary["state"]]


def build_resource_rows(
    kind: str,
    inventory: list[dict[str, object]],
    assignments: dict[str, list[str]],
    statuses: list[dict[str, object]],
) -> list[dict[str, object]]:
    scan_index = {item["name"]: item for item in inventory}
    status_index = {item["name"]: item for item in statuses}
    names = sorted(set(scan_index) | set(assignments) | set(status_index))
    rows: list[dict[str, object]] = []
    for name in names:
        scanned = scan_index.get(name)
        status = status_index.get(name)
        configured_tools = assignments.get(name) or (status.get("configuredTools") if status else [])
        summary_state, summary_message = summarize_entries(status.get("entries", []) if status else [], configured_tools)
        rows.append(
            {
                "kind": kind,
                "name": name,
                "path": (scanned or status or {}).get("path") or (status or {}).get("sourcePath") or "",
                "isDirectory": (scanned or status or {}).get("isDirectory", False),
                "childrenCount": _children_count(scanned),
                "scanned": bool(scanned),
                "configuredTools": configured_tools,
                "entries": status.get("entries", []) if status else [],
                "summaryState": summary_state,
                "summaryMessage": summary_message,
            }
        )
    return rows


def build_issue_rows(snapshot: dict[str, object] | None) -> list[dict[str, object]]:
    if not snapshot:
        return []
    issues: list[dict[str, object]] = []
    for resource in [*snapshot["status"]["skills"], *snapshot["status"]["commands"]]:
        for entry in resource["entries"]:
            if entry["state"] == "healthy":
                continue
            issues.append(
                {
                    "id": f"{resource['kind']}:{resource['name']}:{entry['environmentId']}:{entry['toolId']}",
                    "kind": resource["kind"],
                    "name": resource["name"],
                    "toolId": entry["toolId"],
                    "environmentId": entry["environmentId"],
                    "state": entry["state"],
                    "message": entry["message"],
                    "targetPath": entry.get("targetPath"),
                    "itemCount": entry.get("itemCount", 0),
                }
            )
    return sorted(
        issues,
        key=lambda item: (STATE_PRIORITY[item["state"]], f"{item['kind']}-{item['name']}"),
    )


def count_cleanup_candidates(issues: list[dict[str, object]]) -> int:
    states = {"conflict", "missing", "source_missing"}
    return sum(1 for issue in issues if issue["state"] in states)


def summarize_sync(details: list[dict[str, object]]) -> str:
    success = sum(1 for item in details if item.get("success"))
    skipped = sum(1 for item in details if item.get("skipped"))
    failed = len(details) - success - skipped
    return f"成功 {success} / 跳过 {skipped} / 失败 {failed}"


def summarize_cleanup(details: list[dict[str, object]]) -> str:
    if not details:
        return "没有需要清理的目标"
    success = sum(1 for item in details if item.get("success"))
    return f"已处理 {len(details)} 条，成功 {success} 条"


def count_configured(assignments: dict[str, list[str]]) -> int:
    return sum(1 for tools in assignments.values() if tools)


def overview_stats(snapshot: dict[str, object], issue_count: int, cleanup_candidates: int) -> list[dict[str, str]]:
    managed_skills = count_configured(snapshot["config"]["resources"]["skills"])
    managed_commands = count_configured(snapshot["config"]["resources"]["commands"])
    enabled_targets = 4 + (4 if snapshot["config"]["environments"]["wsl"]["enabled"] else 0)
    mode_label = "复制模式" if snapshot["config"]["syncMode"] == "copy" else "符号链接模式"
    return [
        {"label": "已纳管 Skills", "value": str(managed_skills), "note": f"{len(snapshot['inventory']['skills'])} 个源项"},
        {"label": "已纳管 Commands", "value": str(managed_commands), "note": f"{len(snapshot['inventory']['commands'])} 个源项"},
        {"label": "目标通道", "value": str(enabled_targets), "note": mode_label},
        {"label": "异常条目", "value": str(issue_count), "note": f"{cleanup_candidates} 条可清理"},
    ]


def entry_summary(entries: list[dict[str, object]]) -> str:
    if not entries:
        return "等待状态回填"
    return " | ".join(
        f"{entry['environmentId']}/{entry['toolId']}: {STATE_LABELS.get(entry['state'], entry['state'])}"
        for entry in entries
    )
