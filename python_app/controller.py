from datetime import datetime
from dataclasses import dataclass
from typing import Callable

from copy import deepcopy
from PySide6.QtCore import QObject

from .core.app_service import AppService, create_app_service
from .gui.dashboard import summarize_sync
from .gui.main_window import MainWindow
from .gui.task_runner import TaskThread


@dataclass(frozen=True)
class SyncRequest:
    action: str
    names: list[str]
    assignments: dict[str, dict[str, list[str]]] | None
    commit_targets: dict[str, list[str]] | None
    commit_assignments: dict[str, dict[str, list[str]]] | None
    commit_remove: bool


class AppController(QObject):
    def __init__(self, window: MainWindow, service: AppService | None = None) -> None:
        super().__init__()
        self.window = window
        self.service = service or create_app_service()
        self.logs: list[dict[str, str]] = []
        self.busy: dict[str, bool] = {"initial": True}
        self._workers: list[TaskThread] = []
        self._accumulated_tool_results: list[dict[str, object]] = []
        self._accumulated_gr_results: list[dict[str, object]] = []
        self._auto_skill_check_done = False
        self._connect_signals()

    def start(self) -> None:
        self.refresh_snapshot(reset_error=False, busy_key="initial")

    def refresh_snapshot(self, reset_error: bool = True, busy_key: str = "refresh") -> None:
        self._run_task(
            busy_key,
            "刷新总览",
            self._fetch_snapshot,
            self._after_snapshot,
            log_success=busy_key != "initial",
            reset_error=reset_error,
        )

    def _connect_signals(self) -> None:
        self.window.refresh_requested.connect(lambda: self.refresh_snapshot())
        self.window.sync_all_requested.connect(self._sync_all)
        self.window.rescan_requested.connect(self._rescan_kind)
        self.window.sync_selected_requested.connect(self._sync_selected)
        self.window.global_rule_refresh_requested.connect(
            lambda: self.refresh_snapshot(busy_key="refreshGlobalRules")
        )
        self.window.global_rule_profiles_save_requested.connect(self._save_global_rule_profiles)
        self.window.global_rule_assignments_save_requested.connect(self._save_global_rule_assignments)
        self.window.global_rule_sync_requested.connect(self._sync_global_rules)
        self.window.reload_wsl_requested.connect(lambda: self.refresh_snapshot(busy_key="reloadWsl"))
        self.window.save_config_requested.connect(self._save_config)
        self.window.cleanup_requested.connect(self._cleanup)
        self.window.update_tools_requested.connect(self._update_tools)
        self.window.update_tool_requested.connect(self._update_tool)
        self.window.save_tool_definitions_requested.connect(self._save_tool_definitions)
        self.window.skill_add_requested.connect(self._skill_add)
        self.window.skill_set_url_requested.connect(self._skill_set_url)
        self.window.skill_check_requested.connect(self._skill_check)
        self.window.skill_upgrade_requested.connect(self._skill_upgrade)
        self.window.workflow_action_requested.connect(self._workflow_action)

    def _fetch_snapshot(self) -> dict[str, object]:
        config = self.service.get_config()
        status = self.service.get_status()
        wsl_runtime = self.service.get_wsl_distros()
        return {
            "config": config,
            "status": {**status, "config": config},
            "wslRuntime": wsl_runtime,
            "globalRules": self.service.get_global_rules(),
            "globalRuleStatus": self.service.get_global_rule_status(),
            "inventory": {
                "skills": self.service.scan_resources("skills"),
                "commands": self.service.scan_resources("commands"),
            },
            "skillUpstreams": self.service.get_skill_upstreams(),
            "workflowStatuses": self.service.get_workflow_statuses(),
        }

    def _after_snapshot(self, snapshot: dict[str, object]) -> None:
        self.window.set_snapshot(snapshot)
        self._refresh_update_tool_statuses(snapshot)
        self._auto_check_skill_updates(snapshot)

    def _refresh_update_tool_statuses(self, snapshot: dict[str, object]) -> None:
        if self.busy.get("loadUpdateToolStatuses"):
            return
        config = snapshot.get("config")
        if not isinstance(config, dict):
            return
        tools = config.get("updateTools", {})
        if not isinstance(tools, dict) or not tools:
            return
        wsl_runtime = snapshot.get("wslRuntime", {})
        if not isinstance(wsl_runtime, dict):
            wsl_runtime = {}

        self._run_task(
            "loadUpdateToolStatuses",
            "读取工具版本",
            lambda: self.service.get_update_tool_statuses(config, wsl_runtime),
            lambda statuses: self.window.set_update_tool_statuses(statuses),
            log_success=False,
            reset_error=False,
        )

    def _auto_check_skill_updates(self, snapshot: dict[str, object]) -> None:
        if self._auto_skill_check_done:
            return
        self._auto_skill_check_done = True
        upstreams = snapshot.get("skillUpstreams")
        if not isinstance(upstreams, dict) or not upstreams:
            return
        names = [name for name, entry in upstreams.items()
                 if isinstance(entry, dict) and entry.get("url")]
        if not names:
            return
        self._run_task(
            "autoSkillCheck",
            "自动检查 Skill 更新",
            lambda: self.service.check_skill_updates(names),
            lambda result: self.window.set_skill_update_results(result),
            log_success=False,
            reset_error=False,
        )

    def _sync_all(self) -> None:
        self._run_task("syncAll", "全量同步", self.service.sync_all, self._after_sync_all)

    def _after_sync_all(self, result: dict[str, list[dict[str, object]]]) -> None:
        summary = f"Skills {summarize_sync(result['skills'])}；Commands {summarize_sync(result['commands'])}"
        self.window.set_last_sync_summary(summary)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterSyncAll")

    def _rescan_kind(self, kind: str) -> None:
        key = "scanSkills" if kind == "skills" else "scanCommands"
        self.refresh_snapshot(busy_key=key)

    def _sync_selected(self, kind: str, payload: object) -> None:
        key = "syncSkills" if kind == "skills" else "syncCommands"
        request = self._parse_sync_request(payload)
        label = "同步 Skills" if kind == "skills" else "同步 Commands"
        if request.action == "remove":
            label = "移除 Skills" if kind == "skills" else "移除 Commands"
        if request.action == "upgrade":
            label = "升级 Skills" if kind == "skills" else "升级 Commands"

        def task() -> object:
            if not request.names:
                raise ValueError("未勾选任何条目。")
            self._apply_commit(kind, request)
            if request.action == "remove":
                return self.service.remove_resources(kind, request.names, request.assignments)
            if request.action == "upgrade":
                return self.service.upgrade_resources(kind, request.names, request.assignments)
            return self.service.sync_resources(kind, request.names, request.assignments)

        self._run_task(key, label, task, lambda result: self._after_partial_sync(kind, result))

    def _after_partial_sync(self, kind: str, result: list[dict[str, object]]) -> None:
        self.window.set_last_sync_summary(f"{kind.capitalize()} {summarize_sync(result)}")
        refresh_key = "refreshAfterSyncSkills" if kind == "skills" else "refreshAfterSyncCommands"
        self.refresh_snapshot(reset_error=False, busy_key=refresh_key)

    def _save_config(self, patch: dict[str, object]) -> None:
        self._run_task(
            "saveConfig",
            "保存配置",
            lambda: self.service.save_config(patch),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSaveConfig"),
        )

    def _save_global_rule_profiles(self, payload: dict[str, object]) -> None:
        self._run_task(
            "saveGlobalRuleProfiles",
            "保存全局规则版本",
            lambda: self.service.save_global_rule_profiles(payload),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSaveGlobalRuleProfiles"),
        )

    def _save_global_rule_assignments(
        self,
        assignments: dict[str, dict[str, str | None]],
    ) -> None:
        self._run_task(
            "saveGlobalRuleAssignments",
            "保存全局规则映射",
            lambda: self.service.save_global_rule_assignments(assignments),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSaveGlobalRuleAssignments"),
        )

    def _sync_global_rules(self, payload: object) -> None:
        sync_request = self._parse_global_rule_sync_payload(payload)
        targets = sync_request["targets"]
        assignments = sync_request["assignments"]

        if targets and len(targets) == 1 and assignments is None:
            target = targets[0]
            key = f"syncGlobalRule:{target['environmentId']}:{target['toolId']}"

            def task() -> object:
                return self.service.sync_global_rules(targets, assignments)

            self._run_task(key, "同步全局规则", task, self._after_global_rule_sync_one)
            return

        def task() -> object:
            return self.service.sync_global_rules(targets, assignments)

        self._accumulated_gr_results = []
        self._run_task("syncGlobalRules", "同步全局规则", task, self._after_global_rule_sync)

    def _after_global_rule_sync(self, result: list[dict[str, object]]) -> None:
        success = sum(1 for item in result if item.get("success"))
        skipped = sum(1 for item in result if item.get("skipped"))
        failed = len(result) - success - skipped
        self.window.set_last_sync_summary(
            f"全局规则 成功 {success} · 跳过 {skipped} · 失败 {failed}"
        )
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterSyncGlobalRules")

    def _after_global_rule_sync_one(self, result: list[dict[str, object]]) -> None:
        self._accumulated_gr_results.extend(result)
        all_results = self._accumulated_gr_results
        success = sum(1 for item in all_results if item.get("success"))
        skipped = sum(1 for item in all_results if item.get("skipped"))
        failed = len(all_results) - success - skipped
        self.window.set_last_sync_summary(
            f"全局规则 成功 {success} · 跳过 {skipped} · 失败 {failed}"
        )
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterSyncGlobalRuleOne")

    def _cleanup(self) -> None:
        self._run_task("cleanup", "执行清理", self.service.cleanup_invalid, self._after_cleanup)

    def _after_cleanup(self, result: dict[str, object]) -> None:
        self.window.set_cleanup_result(result)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterCleanup")

    def _update_tools(self, payload: object) -> None:
        target_versions = self._parse_target_versions(payload)
        self._accumulated_tool_results = []
        self._run_task(
            "updateTools",
            "更新工具",
            lambda: self.service.update_tools(target_versions),
            self._after_update_tools,
        )

    def _after_update_tools(self, results: list[dict[str, object]]) -> None:
        self.window.set_tool_results(results)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterUpdateTools")

    def _update_tool(self, name: str, target_version: object) -> None:
        resolved_version = str(target_version or "").strip() or None
        self._run_task(
            f"updateTool:{name}",
            f"更新工具：{name}",
            lambda: self.service.update_tool(name, resolved_version),
            self._after_update_tool,
        )

    def _after_update_tool(self, results: list[dict[str, object]]) -> None:
        self._accumulated_tool_results.extend(results)
        self.window.set_tool_results(list(self._accumulated_tool_results))
        key = f"refreshAfterUpdateTool:{results[0]['name']}" if results else "refreshAfterUpdateTool"
        self.refresh_snapshot(reset_error=False, busy_key=key)

    def _save_tool_definitions(self, definitions: dict[str, dict[str, str]]) -> None:
        self._run_task(
            "saveToolDefinitions",
            "保存工具更新定义",
            lambda: self.service.save_config({"updateTools": definitions}),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSaveToolDefinitions"),
        )

    def _skill_add(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict.")
        name = str(payload.get("name") or "").strip()
        url = str(payload.get("url") or "").strip()
        self._run_task(
            "skillAdd",
            "新增线上 Skill",
            lambda: self.service.add_skill_from_url(name, url),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSkillAdd"),
        )

    def _skill_set_url(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict.")
        raw_names = payload.get("names", [])
        if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
            raise ValueError("names must be a list of strings.")
        url = str(payload.get("url") or "").strip()
        self._run_task(
            "skillSetUrl",
            "设置 Skill 更新 URL",
            lambda: self.service.set_skill_upstream_url(raw_names, url),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSkillSetUrl"),
        )

    def _skill_check(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict.")
        raw_names = payload.get("names", [])
        if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
            raise ValueError("names must be a list of strings.")
        self._run_task(
            "skillCheck",
            "检查 Skill 更新",
            lambda: self.service.check_skill_updates(raw_names),
            lambda result: self.window.set_skill_update_results(result),
            log_success=True,
            reset_error=False,
        )

    def _skill_upgrade(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict.")
        raw_names = payload.get("names", [])
        if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
            raise ValueError("names must be a list of strings.")
        self._run_task(
            "skillUpgrade",
            "下载 Skill 更新",
            lambda: self.service.upgrade_skill_sources(raw_names),
            lambda result: self._after_skill_upgrade(result),
        )

    def _after_skill_upgrade(self, result: list[dict[str, object]]) -> None:
        self.window.set_skill_update_results(result)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterSkillUpgrade")

    def _workflow_action(self, workflow_id: str, target_key: str, action: str) -> None:
        label_map = {
            "install": "安装工作流",
            "uninstall": "卸载工作流",
            "enable": "启用工作流",
            "disable": "禁用工作流",
            "upgrade": "升级工作流",
        }
        label = label_map.get(action, action)
        busy_key = f"workflowAction:{workflow_id}:{target_key}"
        self._run_task(
            busy_key,
            f"{label}：{workflow_id} ({target_key})",
            lambda: self.service.workflow_action(workflow_id, target_key, action),
            lambda _result: self.refresh_snapshot(
                reset_error=False,
                busy_key=f"refreshAfterWorkflowAction:{workflow_id}:{target_key}",
            ),
        )

    def _run_task(
        self,
        busy_key: str,
        label: str,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        log_success: bool = True,
        reset_error: bool = True,
    ) -> None:
        if reset_error:
            self.window.set_error_message(None)
        self._set_busy(busy_key, True)
        worker = TaskThread(task)
        self._workers.append(worker)
        worker.succeeded.connect(lambda result: self._handle_success(label, result, on_success, log_success))
        worker.failed.connect(lambda message: self._handle_error(label, message))
        worker.finished.connect(lambda: self._on_worker_finished(busy_key, worker))
        worker.start()

    def _handle_success(
        self,
        label: str,
        result: object,
        on_success: Callable[[object], None],
        log_success: bool,
    ) -> None:
        on_success(result)
        if log_success:
            self._push_log(label, "执行完成", "ok")

    def _handle_error(self, label: str, message: str) -> None:
        self.window.set_error_message(f"{label}: {message}")
        self._push_log(label, message, "error")

    def _on_worker_finished(self, busy_key: str, worker: TaskThread) -> None:
        self._set_busy(busy_key, False)
        self._workers = [item for item in self._workers if item is not worker]

    def _set_busy(self, key: str, value: bool) -> None:
        self.busy[key] = value
        self.window.set_busy(self.busy)

    def _push_log(self, label: str, detail: str, status: str) -> None:
        self.logs = [
            {
                "label": label,
                "detail": detail,
                "status": status,
                "time": datetime.now().strftime("%H:%M:%S"),
            },
            *self.logs,
        ][:6]
        self.window.set_logs(self.logs)

    def _parse_sync_request(self, payload: object) -> SyncRequest:
        if isinstance(payload, list):
            if any(not isinstance(name, str) for name in payload):
                raise ValueError("names must be a list of strings.")
            return SyncRequest("sync", payload, None, None, None, False)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict or list.")

        action = payload.get("action", "sync")
        if action not in {"sync", "remove", "upgrade"}:
            raise ValueError("action must be 'sync' or 'remove' or 'upgrade'.")
        raw_names = payload.get("names", [])
        if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
            raise ValueError("names must be a list of strings.")

        assignments = None
        if "assignments" in payload:
            raw_assignments = payload.get("assignments")
            if raw_assignments is not None and not isinstance(raw_assignments, dict):
                raise ValueError("assignments must be a dict.")
            assignments = raw_assignments

        commit_targets = None
        if "commitTargets" in payload:
            raw_commit_targets = payload.get("commitTargets")
            if raw_commit_targets is not None and not isinstance(raw_commit_targets, dict):
                raise ValueError("commitTargets must be a dict.")
            commit_targets = raw_commit_targets

        commit_assignments = None
        if "commitAssignments" in payload:
            raw_commit_assignments = payload.get("commitAssignments")
            if raw_commit_assignments is not None and not isinstance(raw_commit_assignments, dict):
                raise ValueError("commitAssignments must be a dict.")
            commit_assignments = raw_commit_assignments

        commit_remove = bool(payload.get("commitRemove", False))
        if commit_targets is not None and (commit_assignments is not None or commit_remove):
            raise ValueError("commitTargets cannot be combined with commitAssignments/commitRemove.")
        if commit_assignments is not None and commit_remove:
            raise ValueError("commitAssignments cannot be combined with commitRemove.")
        if commit_targets is not None and len(raw_names) != 1:
            raise ValueError("commitTargets requires exactly one resource name.")
        if commit_assignments is not None and set(raw_names) != set(commit_assignments.keys()):
            raise ValueError("commitAssignments keys must match names.")
        return SyncRequest(action, raw_names, assignments, commit_targets, commit_assignments, commit_remove)

    def _apply_commit(self, kind: str, request: SyncRequest) -> None:
        if request.commit_targets is not None:
            name = request.names[0]
            config = self.service.get_config()
            current = config["resources"][kind]
            next_assignments = deepcopy(current) if isinstance(current, dict) else {}
            has_targets = any(request.commit_targets.get(environment_id) for environment_id in ("windows", "wsl"))
            if has_targets:
                next_assignments[name] = request.commit_targets
            else:
                next_assignments.pop(name, None)
            self.service.replace_resource_map(kind, next_assignments)
            return

        if request.commit_assignments is not None:
            config = self.service.get_config()
            current = config["resources"][kind]
            next_assignments = deepcopy(current) if isinstance(current, dict) else {}
            for name, targets in request.commit_assignments.items():
                next_assignments[name] = targets
            self.service.replace_resource_map(kind, next_assignments)

        if request.commit_remove:
            config = self.service.get_config()
            current = config["resources"][kind]
            next_assignments = deepcopy(current) if isinstance(current, dict) else {}
            for name in request.names:
                next_assignments.pop(name, None)
            self.service.replace_resource_map(kind, next_assignments)

    def _parse_global_rule_sync_payload(
        self,
        payload: object,
    ) -> dict[str, object]:
        if isinstance(payload, dict):
            raw_targets = payload.get("targets")
            raw_assignments = payload.get("assignments")
            if raw_assignments is not None and not isinstance(raw_assignments, dict):
                raise ValueError("global rule sync assignments must be a dict or null.")
            return {
                "targets": self._parse_global_rule_targets(raw_targets),
                "assignments": raw_assignments,
            }
        return {
            "targets": self._parse_global_rule_targets(payload),
            "assignments": None,
        }

    def _parse_target_versions(self, payload: object) -> dict[str, str] | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise ValueError("target versions payload must be a dict or null.")
        normalized: dict[str, str] = {}
        for name, version in payload.items():
            if not isinstance(name, str):
                raise ValueError("target version key must be a string.")
            normalized_name = name.strip()
            normalized_version = str(version or "").strip()
            if not normalized_name or not normalized_version:
                continue
            normalized[normalized_name] = normalized_version
        return normalized or None

    def _parse_global_rule_targets(
        self,
        payload: object,
    ) -> list[dict[str, str]] | None:
        if payload is None:
            return None
        if not isinstance(payload, list):
            raise ValueError("global rule sync payload must be a list or null.")
        normalized: list[dict[str, str]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("global rule sync target must be a dict.")
            environment_id = str(item.get("environmentId") or "").strip()
            tool_id = str(item.get("toolId") or "").strip()
            if not environment_id or not tool_id:
                raise ValueError("global rule sync target requires environmentId and toolId.")
            normalized.append(
                {
                    "environmentId": environment_id,
                    "toolId": tool_id,
                }
            )
        return normalized
