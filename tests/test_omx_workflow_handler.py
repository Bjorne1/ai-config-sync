import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python_app.core.omx_workflow_handler import (
    OH_MY_CODEX_PACKAGE,
    OH_MY_CODEX_TARBALL_URL,
    OhMyCodexHandler,
    OmxPackageInfo,
    OmxCommandRunner,
)
from python_app.core.workflow_handlers import TargetContext, TargetStatus
from python_app.core.workflow_registry import WorkflowDefinition
from python_app.core.workflow_service import scan_workflow_statuses


def _completed(args: list[str], stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


class FakeRunner:
    def __init__(self, outputs: list[subprocess.CompletedProcess[str]], on_call=None) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict[str, object]] = []
        self.on_call = on_call

    def run(self, ctx: TargetContext, args, *, cwd):
        self.calls.append({"ctx": ctx, "args": list(args), "cwd": cwd})
        if self.on_call is not None:
            self.on_call(ctx, list(args), cwd)
        if not self.outputs:
            raise AssertionError(f"unexpected call: {args}")
        return self.outputs.pop(0)


class StaticHandler:
    def __init__(self, status: TargetStatus) -> None:
        self._status = status

    def detect_status(self, _ctx: TargetContext) -> TargetStatus:
        return self._status

    def install(self, _ctx: TargetContext):
        raise NotImplementedError

    def uninstall(self, _ctx: TargetContext):
        raise NotImplementedError

    def enable(self, _ctx: TargetContext):
        raise NotImplementedError

    def disable(self, _ctx: TargetContext):
        raise NotImplementedError

    def upgrade(self, _ctx: TargetContext):
        raise NotImplementedError


class OmxWorkflowHandlerTests(unittest.TestCase):
    def _create_package(self, modules_dir: Path, version: str = "0.12.4") -> Path:
        package_dir = modules_dir / OH_MY_CODEX_PACKAGE
        (package_dir / "dist" / "cli").mkdir(parents=True)
        (package_dir / "skills" / "deep-interview").mkdir(parents=True)
        (package_dir / "prompts").mkdir(parents=True)
        (package_dir / "prompts" / "ralph.md").write_text("# prompt", encoding="utf-8")
        (package_dir / "package.json").write_text(
            f'{{"name":"{OH_MY_CODEX_PACKAGE}","version":"{version}"}}',
            encoding="utf-8",
        )
        (package_dir / "dist" / "cli" / "omx.js").write_text("console.log('ok')", encoding="utf-8")
        return package_dir

    def _create_source_package(self, modules_dir: Path, version: str = "0.12.4") -> Path:
        package_dir = modules_dir / OH_MY_CODEX_PACKAGE
        package_dir.mkdir(parents=True)
        (package_dir / "skills" / "deep-interview").mkdir(parents=True)
        (package_dir / "prompts").mkdir(parents=True)
        (package_dir / "prompts" / "ralph.md").write_text("# prompt", encoding="utf-8")
        (package_dir / "package.json").write_text(
            f'{{"name":"{OH_MY_CODEX_PACKAGE}","version":"{version}"}}',
            encoding="utf-8",
        )
        return package_dir

    def test_detect_status_distinguishes_installed_and_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            self._create_package(modules_dir)
            codex_home = root / "home"
            (codex_home / ".codex").mkdir(parents=True)
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner([_completed(["npm", "root", "-g"], stdout=str(modules_dir))])
            handler = OhMyCodexHandler(runner=runner)

            status = handler.detect_status(ctx)

            self.assertTrue(status.available)
            self.assertTrue(status.installed)
            self.assertFalse(status.enabled)
            self.assertFalse(status.metadata["agentsFileExists"])

            (codex_home / ".codex" / "config.toml").write_text("# oh-my-codex", encoding="utf-8")
            (codex_home / ".codex" / "AGENTS.md").write_text("# user", encoding="utf-8")
            runner.outputs.append(_completed(["npm", "root", "-g"], stdout=str(modules_dir)))

            enabled_status = handler.detect_status(ctx)

            self.assertTrue(enabled_status.enabled)
            self.assertTrue(enabled_status.metadata["agentsFileExists"])
            self.assertTrue(str(enabled_status.metadata["agentsFilePath"]).endswith(r".codex\AGENTS.md"))

    def test_detect_status_blocks_when_codex_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(root / "home"))
            runner = FakeRunner([])
            handler = OhMyCodexHandler(runner=runner)

            status = handler.detect_status(ctx)

            self.assertFalse(status.available)
            self.assertFalse(status.installed)
            self.assertIn("请先安装 Codex", status.error or "")

    def test_install_requires_explicit_agents_overwrite_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = root / "home"
            (codex_home / ".codex").mkdir(parents=True)
            (codex_home / ".codex" / "AGENTS.md").write_text("# USER RULES\n", encoding="utf-8")
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            handler = OhMyCodexHandler(runner=FakeRunner([]))

            with self.assertRaisesRegex(RuntimeError, "请先确认是否覆盖"):
                handler.install(ctx)

    def test_install_uses_setup_without_force_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            package_dir = self._create_source_package(modules_dir)
            built_entry = package_dir / "dist" / "cli" / "omx.js"
            codex_home = root / "home"
            codex_dir = codex_home / ".codex"
            codex_dir.mkdir(parents=True)
            (codex_dir / "AGENTS.md").write_text("# USER RULES\n", encoding="utf-8")
            (codex_dir / "config.toml").write_text("before-config\n", encoding="utf-8")
            (codex_dir / "hooks.json").write_text('{"before": true}\n', encoding="utf-8")
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))

            def on_call(_ctx, args, _cwd):
                if args == ["npm", "run", "build"]:
                    built_entry.parent.mkdir(parents=True, exist_ok=True)
                    built_entry.write_text("console.log('ok')", encoding="utf-8")

            runner = FakeRunner(
                [
                    _completed(["npm", "install", "-g", OH_MY_CODEX_TARBALL_URL]),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["npm", "install", "--include=dev"]),
                    _completed(["npm", "run", "build"]),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["node", str(built_entry), "setup", "--scope", "user"]),
                    _completed(["node", str(built_entry), "doctor"], stdout="[OK] Codex home: ready"),
                ],
                on_call=on_call,
            )
            handler = OhMyCodexHandler(runner=runner, latest_commit_resolver=lambda: "abcdef123456")

            with mock.patch("python_app.core.omx_workflow_handler.WINDOWS_OMX_BASE", root / "runtime"):
                result = handler.install_with_options(ctx, force_agents_overwrite=False)

            self.assertEqual(result["commit"], "abcdef123456")
            self.assertEqual(runner.calls[0]["args"], ["npm", "install", "-g", OH_MY_CODEX_TARBALL_URL])
            self.assertEqual(runner.calls[2]["args"], ["npm", "install", "--include=dev"])
            self.assertEqual(runner.calls[3]["args"], ["npm", "run", "build"])
            self.assertEqual(
                runner.calls[5]["args"],
                ["node", str(built_entry), "setup", "--scope", "user"],
            )
            self.assertEqual(
                runner.calls[6]["args"],
                ["node", str(built_entry), "doctor"],
            )
            self.assertTrue(result["doctor"]["allOk"])
            self.assertEqual(result["doctorWarnings"], [])
            manifest_path = root / "runtime" / "workflow-backups" / "oh-my-codex" / "windows" / "codex" / "manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = {entry["name"]: entry for entry in manifest["entries"]}
            self.assertTrue(entries["AGENTS.md"]["existed"])
            self.assertTrue(entries["config.toml"]["existed"])
            self.assertTrue(entries["hooks.json"]["existed"])
            self.assertFalse(entries["prompts"]["existed"])
            self.assertEqual(
                (manifest_path.parent / "payload" / "AGENTS.md").read_text(encoding="utf-8"),
                "# USER RULES\n",
            )

    def test_install_uses_force_when_user_allows_agents_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            package_dir = self._create_package(modules_dir)
            codex_home = root / "home"
            (codex_home / ".codex").mkdir(parents=True)
            (codex_home / ".codex" / "AGENTS.md").write_text("# USER RULES\n", encoding="utf-8")
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner(
                [
                    _completed(["npm", "install", "-g", OH_MY_CODEX_TARBALL_URL]),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["node", str(package_dir / "dist" / "cli" / "omx.js"), "setup", "--force", "--scope", "user"]),
                    _completed(["node", str(package_dir / "dist" / "cli" / "omx.js"), "doctor"], stdout="[OK] AGENTS.md: found"),
                ]
            )
            handler = OhMyCodexHandler(runner=runner, latest_commit_resolver=lambda: "abcdef123456")

            with mock.patch("python_app.core.omx_workflow_handler.WINDOWS_OMX_BASE", root / "runtime"):
                handler.install_with_options(ctx, force_agents_overwrite=True)

            self.assertEqual(
                runner.calls[3]["args"],
                ["node", str(package_dir / "dist" / "cli" / "omx.js"), "setup", "--force", "--scope", "user"],
            )
            self.assertEqual(
                runner.calls[4]["args"],
                ["node", str(package_dir / "dist" / "cli" / "omx.js"), "doctor"],
            )

    def test_enable_doctor_warning_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            package_dir = self._create_package(modules_dir)
            codex_home = root / "home"
            codex_dir = codex_home / ".codex"
            codex_dir.mkdir(parents=True)
            (codex_dir / "AGENTS.md").write_text("# USER RULES\n", encoding="utf-8")
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner(
                [
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["node", str(package_dir / "dist" / "cli" / "omx.js"), "setup", "--force", "--scope", "user"]),
                    _completed(["node", str(package_dir / "dist" / "cli" / "omx.js"), "doctor"], stdout="[WARN] MCP Servers: missing entries"),
                ]
            )
            handler = OhMyCodexHandler(runner=runner)

            with mock.patch("python_app.core.omx_workflow_handler.WINDOWS_OMX_BASE", root / "runtime"):
                result = handler.enable_with_options(ctx, force_agents_overwrite=True)

            self.assertTrue(result["success"])
            self.assertIn("doctor 发现 1 项非 OK", result["message"])
            self.assertEqual(result["doctorWarnings"], ["[WARN] MCP Servers: missing entries"])

    def test_disable_restores_original_files_and_removes_generated_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            package_dir = self._create_package(modules_dir)
            codex_home = root / "home"
            codex_dir = codex_home / ".codex"
            codex_dir.mkdir(parents=True)
            (codex_dir / "AGENTS.md").write_text("# USER RULES\n", encoding="utf-8")
            (codex_dir / "config.toml").write_text("before-config\n", encoding="utf-8")
            (codex_dir / "hooks.json").write_text('{"before": true}\n', encoding="utf-8")
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner(
                [
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["node", str(package_dir / "dist" / "cli" / "omx.js"), "uninstall", "--scope", "user"]),
                ]
            )
            handler = OhMyCodexHandler(runner=runner)

            with mock.patch("python_app.core.omx_workflow_handler.WINDOWS_OMX_BASE", root / "runtime"):
                handler._backup_existing_state(ctx)
                (codex_dir / "AGENTS.md").write_text("# OMX RULES\n", encoding="utf-8")
                (codex_dir / "config.toml").write_text("omx-config\n", encoding="utf-8")
                (codex_dir / "hooks.json").write_text('{"omx": true}\n', encoding="utf-8")
                (codex_dir / "prompts").mkdir()
                (codex_dir / "prompts" / "extra.md").write_text("# extra\n", encoding="utf-8")

                result = handler.disable(ctx)

            self.assertTrue(result["success"])
            self.assertIn("恢复原有 Codex 配置", result["message"])
            self.assertEqual((codex_dir / "AGENTS.md").read_text(encoding="utf-8"), "# USER RULES\n")
            self.assertEqual((codex_dir / "config.toml").read_text(encoding="utf-8"), "before-config\n")
            self.assertEqual((codex_dir / "hooks.json").read_text(encoding="utf-8"), '{"before": true}\n')
            self.assertFalse((codex_dir / "prompts").exists())
            self.assertFalse((root / "runtime" / "workflow-backups" / "oh-my-codex" / "windows" / "codex").exists())

    def test_upgrade_keeps_disabled_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            self._create_package(modules_dir)
            codex_home = root / "home"
            (codex_home / ".codex").mkdir(parents=True)
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner(
                [
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["npm", "install", "-g", OH_MY_CODEX_TARBALL_URL]),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                    _completed(["npm", "root", "-g"], stdout=str(modules_dir)),
                ]
            )
            handler = OhMyCodexHandler(runner=runner, latest_commit_resolver=lambda: "fedcba987654")

            with mock.patch("python_app.core.omx_workflow_handler.WINDOWS_OMX_BASE", root / "runtime"):
                result = handler.upgrade(ctx)

            self.assertTrue(result["success"])
            self.assertEqual(len(runner.calls), 4)
            self.assertTrue(all(call["args"][0] != "node" for call in runner.calls))

    def test_wsl_package_resolution_uses_linux_entry_and_unc_package_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_dir = self._create_package(root / "wsl-package")
            runner = FakeRunner([_completed(["npm", "root", "-g"], stdout="/usr/local/lib/node_modules")])
            handler = OhMyCodexHandler(runner=runner)
            ctx = TargetContext(
                environment_id="wsl",
                tool_id="codex",
                home_dir=r"\\wsl.localhost\Ubuntu\home\me",
                wsl_distro="Ubuntu",
            )

            with mock.patch(
                "python_app.core.omx_workflow_handler._wsl_path_to_unc",
                return_value=package_dir,
            ):
                package = handler._find_installed_package(ctx)

            self.assertIsNotNone(package)
            self.assertEqual(
                package.entry_script,
                "/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js",
            )
            self.assertEqual(
                package.command_dir,
                "/usr/local/lib/node_modules/oh-my-codex",
            )

    def test_partial_source_install_is_treated_as_repairable_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            modules_dir = root / "node_modules"
            modules_dir.mkdir()
            package_dir = modules_dir / OH_MY_CODEX_PACKAGE
            package_dir.mkdir()
            (package_dir / "package.json").write_text(
                f'{{"name":"{OH_MY_CODEX_PACKAGE}","version":"0.12.4"}}',
                encoding="utf-8",
            )
            codex_home = root / "home"
            (codex_home / ".codex").mkdir(parents=True)
            ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=str(codex_home))
            runner = FakeRunner([_completed(["npm", "root", "-g"], stdout=str(modules_dir))])
            handler = OhMyCodexHandler(runner=runner)

            status = handler.detect_status(ctx)

            self.assertTrue(status.available)
            self.assertFalse(status.installed)
            self.assertFalse(status.enabled)

    def test_wsl_runner_builds_shell_command_with_linux_cwd(self) -> None:
        runner = OmxCommandRunner()
        ctx = TargetContext(
            environment_id="wsl",
            tool_id="codex",
            home_dir=r"\\wsl.localhost\Ubuntu\home\me",
            wsl_distro="Ubuntu",
        )
        captured: dict[str, object] = {}

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return _completed(args)

        with mock.patch("python_app.core.omx_workflow_handler.subprocess.run", side_effect=fake_run):
            runner.run(ctx, ["npm", "root", "-g"], cwd="/home/me/.ai-config-sync/workflow-runtime")

        self.assertEqual(captured["args"][0:6], ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-ic"])
        self.assertIn("mkdir -p /home/me/.ai-config-sync/workflow-runtime", captured["args"][6])
        self.assertIn("npm root -g", captured["args"][6])

    def test_windows_runner_wraps_npm_with_cmd(self) -> None:
        runner = OmxCommandRunner()
        ctx = TargetContext(environment_id="windows", tool_id="codex", home_dir=r"C:\Users\me")
        captured: dict[str, object] = {}

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return _completed(args)

        with mock.patch("python_app.core.omx_workflow_handler.subprocess.run", side_effect=fake_run):
            runner.run(ctx, ["npm", "root", "-g"], cwd=r"C:\temp\omx")

        self.assertEqual(captured["args"][0:3], ["cmd.exe", "/c", "npm"])
        self.assertEqual(captured["args"][3:], ["root", "-g"])

    def test_ensure_shell_command_creates_local_omx_link_in_wsl(self) -> None:
        runner = FakeRunner(
            [
                _completed(["mkdir", "-p", "/home/me/.local/bin"]),
                _completed(["ln", "-sf", "/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js", "/home/me/.local/bin/omx"]),
                _completed(["chmod", "+x", "/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js"]),
            ]
        )
        handler = OhMyCodexHandler(runner=runner)
        ctx = TargetContext(
            environment_id="wsl",
            tool_id="codex",
            home_dir=r"\\wsl.localhost\Ubuntu\home\me",
            wsl_distro="Ubuntu",
        )
        package = OmxPackageInfo(
            package_dir=Path(r"\\wsl.localhost\Ubuntu\usr\local\lib\node_modules\oh-my-codex"),
            version="0.12.4",
            entry_script="/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js",
            command_dir="/usr/local/lib/node_modules/oh-my-codex",
        )

        handler._ensure_shell_command(ctx, package)

        self.assertEqual(runner.calls[0]["args"], ["mkdir", "-p", "/home/me/.local/bin"])
        self.assertEqual(
            runner.calls[1]["args"],
            ["ln", "-sf", "/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js", "/home/me/.local/bin/omx"],
        )
        self.assertEqual(
            runner.calls[2]["args"],
            ["chmod", "+x", "/usr/local/lib/node_modules/oh-my-codex/dist/cli/omx.js"],
        )

    def test_detect_status_returns_clear_message_when_wsl_node_missing(self) -> None:
        runner = FakeRunner(
            [
                _completed(["npm", "root", "-g"], stderr="sh: 1: npm: not found", returncode=127),
            ]
        )
        handler = OhMyCodexHandler(runner=runner)

        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir)
            codex_dir = home_dir / ".codex"
            codex_dir.mkdir()
            ctx = TargetContext(
                environment_id="wsl",
                tool_id="codex",
                home_dir=str(home_dir),
                wsl_distro="Ubuntu",
            )
            with mock.patch.object(handler, "_runtime_dir_for", return_value="/tmp/omx"):
                status = handler.detect_status(ctx)

        self.assertFalse(status.available)
        self.assertFalse(status.installed)
        self.assertIn("Node.js/npm", status.error or "")

    def test_scan_workflow_statuses_reuses_recorded_commit_for_omx(self) -> None:
        environments = {
            "windows": {
                "roots": {"codex": r"C:\Users\me\.codex"},
                "error": None,
            },
            "wsl": {
                "roots": {"codex": None},
                "error": "未发现 WSL 发行版",
            },
        }
        definition = WorkflowDefinition(
            workflow_id="oh-my-codex",
            label="oh-my-codex",
            description="test",
            repo_url="https://github.com/Bjorne1/oh-my-codex",
            supported_tools=("codex",),
            handler_factory=lambda _tool_id: StaticHandler(
                TargetStatus(
                    available=True,
                    installed=True,
                    enabled=True,
                    version=None,
                    metadata={
                        "agentsFileExists": True,
                        "agentsFilePath": r"C:\Users\me\.codex\AGENTS.md",
                    },
                )
            ),
        )
        workflow_state = {
            "oh-my-codex": {
                "targets": {
                    "windows:codex": {
                        "installedCommit": "abcdef123456",
                        "installedVersion": "0.12.4",
                    }
                }
            }
        }

        with mock.patch.dict(
            "python_app.core.workflow_service.WORKFLOW_REGISTRY",
            {"oh-my-codex": definition},
            clear=True,
        ):
            statuses = scan_workflow_statuses(environments, workflow_state)

        self.assertEqual(statuses[0]["targets"]["windows:codex"]["version"], "0.12.4")
        self.assertEqual(statuses[0]["targets"]["windows:codex"]["installedCommit"], "abcdef123456")
        self.assertTrue(statuses[0]["targets"]["windows:codex"]["agentsFileExists"])


if __name__ == "__main__":
    unittest.main()
