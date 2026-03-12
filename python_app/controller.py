from datetime import datetime
from typing import Callable

from copy import deepcopy
from PySide6.QtCore import QObject

from .core.app_service import AppService, create_app_service
from .gui.dashboard import summarize_sync
from .gui.main_window import MainWindow
from .gui.task_runner import TaskThread


class AppController(QObject):
    def __init__(self, window: MainWindow, service: AppService | None = None) -> None:
        super().__init__()
        self.window = window
        self.service = service or create_app_service()
        self.logs: list[dict[str, str]] = []
        self.busy: dict[str, bool] = {"initial": True}
        self._workers: list[TaskThread] = []
        self._connect_signals()

    def start(self) -> None:
        self.refresh_snapshot(reset_error=False, busy_key="initial")

    def refresh_snapshot(self, reset_error: bool = True, busy_key: str = "refresh") -> None:
        self._run_task(
            busy_key,
            "刷新总览",
            self._fetch_snapshot,
            lambda snapshot: self.window.set_snapshot(snapshot),
            log_success=busy_key != "initial",
            reset_error=reset_error,
        )

    def _connect_signals(self) -> None:
        self.window.refresh_requested.connect(lambda: self.refresh_snapshot())
        self.window.sync_all_requested.connect(self._sync_all)
        self.window.rescan_requested.connect(self._rescan_kind)
        self.window.save_assignments_requested.connect(self._save_assignments)
        self.window.sync_selected_requested.connect(self._sync_selected)
        self.window.reload_wsl_requested.connect(lambda: self.refresh_snapshot(busy_key="reloadWsl"))
        self.window.save_config_requested.connect(self._save_config)
        self.window.cleanup_requested.connect(self._cleanup)
        self.window.update_tools_requested.connect(self._update_tools)
        self.window.save_tool_definitions_requested.connect(self._save_tool_definitions)

    def _fetch_snapshot(self) -> dict[str, object]:
        config = self.service.get_config()
        status = self.service.get_status()
        wsl_runtime = self.service.get_wsl_distros()
        return {
            "config": config,
            "status": {**status, "config": config},
            "wslRuntime": wsl_runtime,
            "inventory": {
                "skills": self.service.scan_resources("skills"),
                "commands": self.service.scan_resources("commands"),
            },
        }

    def _sync_all(self) -> None:
        self._run_task("syncAll", "全量同步", self.service.sync_all, self._after_sync_all)

    def _after_sync_all(self, result: dict[str, list[dict[str, object]]]) -> None:
        summary = f"Skills {summarize_sync(result['skills'])}；Commands {summarize_sync(result['commands'])}"
        self.window.set_last_sync_summary(summary)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterSyncAll")

    def _rescan_kind(self, kind: str) -> None:
        key = "scanSkills" if kind == "skills" else "scanCommands"
        self.refresh_snapshot(busy_key=key)

    def _save_assignments(self, kind: str, assignments: dict[str, list[str]]) -> None:
        key = "saveSkills" if kind == "skills" else "saveCommands"
        label = "保存 Skills 分配" if kind == "skills" else "保存 Commands 分配"
        task = lambda: self.service.replace_resource_map(kind, assignments)
        self._run_task(key, label, task, lambda _result: self.refresh_snapshot(False, f"refreshAfter{key.title()}"))

    def _sync_selected(self, kind: str, payload: object) -> None:
        key = "syncSkills" if kind == "skills" else "syncCommands"
        label = "同步 Skills" if kind == "skills" else "同步 Commands"
        names: list[str] = []
        assignments = None
        action = "sync"
        commit_targets = None
        if isinstance(payload, dict):
            raw_action = payload.get("action")
            action = raw_action if raw_action in {"sync", "remove"} else "sync"
            raw_names = payload.get("names")
            raw_assignments = payload.get("assignments")
            raw_commit_targets = payload.get("commitTargets")
            names = raw_names if isinstance(raw_names, list) else []
            assignments = raw_assignments if isinstance(raw_assignments, dict) else None
            commit_targets = raw_commit_targets if isinstance(raw_commit_targets, dict) else None
        elif isinstance(payload, list):
            names = payload
        if action == "remove":
            label = "移除 Skills" if kind == "skills" else "移除 Commands"

        def task() -> object:
            if commit_targets is not None:
                if len(names) != 1 or not isinstance(names[0], str):
                    raise ValueError("commitTargets requires exactly one resource name.")
                config = self.service.get_config()
                current = config["resources"][kind]
                next_assignments = deepcopy(current) if isinstance(current, dict) else {}
                has_targets = any(commit_targets.get(environment_id) for environment_id in ("windows", "wsl"))
                if has_targets:
                    next_assignments[names[0]] = commit_targets
                else:
                    next_assignments.pop(names[0], None)
                self.service.replace_resource_map(kind, next_assignments)
            if action == "remove":
                return self.service.remove_resources(kind, names, assignments)
            return self.service.sync_resources(kind, names, assignments)

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

    def _cleanup(self) -> None:
        self._run_task("cleanup", "执行清理", self.service.cleanup_invalid, self._after_cleanup)

    def _after_cleanup(self, result: dict[str, object]) -> None:
        self.window.set_cleanup_result(result)
        self.refresh_snapshot(reset_error=False, busy_key="refreshAfterCleanup")

    def _update_tools(self) -> None:
        self._run_task("updateTools", "更新工具", self.service.update_tools, self.window.set_tool_results)

    def _save_tool_definitions(self, definitions: dict[str, dict[str, str]]) -> None:
        self._run_task(
            "saveToolDefinitions",
            "保存工具更新定义",
            lambda: self.service.save_config({"updateTools": definitions}),
            lambda _result: self.refresh_snapshot(False, "refreshAfterSaveToolDefinitions"),
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
