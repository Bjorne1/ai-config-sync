from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

from .process_utils import hidden_subprocess_kwargs
from .workflow_handlers import TargetContext, TargetStatus, WorkflowHandler


OH_MY_CODEX_TARBALL_URL = "https://codeload.github.com/Bjorne1/oh-my-codex/tar.gz/refs/heads/main"
OH_MY_CODEX_PACKAGE = "oh-my-codex"
OH_MY_CODEX_LABEL = "oh-my-codex"
OMX_RUNTIME_DIR_NAME = "workflow-runtime"
OMX_BACKUP_DIR_NAME = "workflow-backups"
OMX_WORK_DIR_NAME = "oh-my-codex"
WINDOWS_OMX_BASE = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "ai-config-sync"
CONFIG_MARKER = "oh-my-codex"
OMX_BACKUP_ITEMS = (
    "AGENTS.md",
    "config.toml",
    "hooks.json",
    "prompts",
    "skills",
    "agents",
    "native-agents",
)


@dataclass(frozen=True)
class OmxPackageInfo:
    package_dir: Path
    version: str | None
    entry_script: str
    command_dir: str


def _wsl_path_to_unc(distro: str, linux_path: str) -> Path:
    relative = linux_path.lstrip("/").replace("/", "\\")
    return Path(f"\\\\wsl.localhost\\{distro}\\{relative}")


def _windows_runtime_dir() -> Path:
    return WINDOWS_OMX_BASE / OMX_RUNTIME_DIR_NAME / OMX_WORK_DIR_NAME / "windows"


def _windows_backup_dir(ctx: TargetContext) -> Path:
    env_name = ctx.environment_id
    if ctx.environment_id == "wsl":
        env_name = f"wsl-{ctx.wsl_distro or 'default'}"
    return WINDOWS_OMX_BASE / OMX_BACKUP_DIR_NAME / OMX_WORK_DIR_NAME / env_name / ctx.tool_id


def _wsl_home_dir(ctx: TargetContext) -> PurePosixPath:
    if not ctx.wsl_distro:
        raise RuntimeError("未选择 WSL 发行版")
    prefix = f"\\\\wsl.localhost\\{ctx.wsl_distro}\\"
    raw = str(ctx.home_dir or "")
    if not raw.startswith(prefix):
        raise RuntimeError(f"无法解析 WSL 主目录: {ctx.home_dir}")
    relative = raw[len(prefix):].replace("\\", "/").strip("/")
    return PurePosixPath("/") / PurePosixPath(relative) if relative else PurePosixPath("/")


def _wsl_runtime_dir(ctx: TargetContext) -> PurePosixPath:
    distro = ctx.wsl_distro or "default"
    return _wsl_home_dir(ctx) / ".ai-config-sync" / OMX_RUNTIME_DIR_NAME / OMX_WORK_DIR_NAME / distro


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def _node_runtime_missing_message(environment_id: str) -> str:
    if environment_id == "wsl":
        return "WSL 中未安装 Node.js/npm，请先安装后再使用 oh-my-codex。"
    return "Windows 中未安装 Node.js/npm，或 GUI 进程未拿到它们的可执行路径。请先确认 Node.js 已安装。"


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _iter_package_skill_names(package_dir: Path) -> set[str]:
    skills_dir = package_dir / "skills"
    if not skills_dir.exists():
        return set()
    return {entry.name for entry in skills_dir.iterdir() if entry.is_dir()}


def _iter_package_prompt_names(package_dir: Path) -> set[str]:
    prompts_dir = package_dir / "prompts"
    if not prompts_dir.exists():
        return set()
    return {entry.name for entry in prompts_dir.iterdir() if entry.is_file() and entry.suffix == ".md"}


def _has_matching_children(root: Path, expected_names: set[str]) -> bool:
    if not root.exists() or not expected_names:
        return False
    present = {entry.name for entry in root.iterdir()}
    return bool(present & expected_names)


def _config_contains_omx(config_path: Path) -> bool:
    if not config_path.exists():
        return False
    content = config_path.read_text(encoding="utf-8", errors="ignore")
    return CONFIG_MARKER in content


def _hooks_contains_omx(hooks_path: Path) -> bool:
    if not hooks_path.exists():
        return False
    content = hooks_path.read_text(encoding="utf-8", errors="ignore")
    return CONFIG_MARKER in content


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


class OmxCommandRunner:
    def run(
        self,
        ctx: TargetContext,
        args: Sequence[str],
        *,
        cwd: str | Path,
    ) -> subprocess.CompletedProcess[str]:
        if ctx.environment_id == "wsl":
            return self._run_wsl(ctx, args, cwd)
        return self._run_windows(args, cwd)

    def _run_windows(
        self,
        args: Sequence[str],
        cwd: str | Path,
    ) -> subprocess.CompletedProcess[str]:
        Path(cwd).mkdir(parents=True, exist_ok=True)
        command = list(args)
        if command and command[0].lower() in {"npm", "node"}:
            command = ["cmd.exe", "/c", *command]
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=180,
            **hidden_subprocess_kwargs(),
        )

    def _run_wsl(
        self,
        ctx: TargetContext,
        args: Sequence[str],
        cwd: str | Path,
    ) -> subprocess.CompletedProcess[str]:
        if not ctx.wsl_distro:
            raise RuntimeError("未选择 WSL 发行版")
        quoted_args = " ".join(shlex.quote(str(arg)) for arg in args)
        wsl_cwd = str(cwd)
        script = f"mkdir -p {shlex.quote(wsl_cwd)} && cd {shlex.quote(wsl_cwd)} && {quoted_args}"
        return subprocess.run(
            ["wsl.exe", "-d", ctx.wsl_distro, "--", "bash", "-ic", script],
            capture_output=True,
            text=True,
            timeout=180,
            **hidden_subprocess_kwargs(),
        )


class OhMyCodexHandler(WorkflowHandler):
    def __init__(
        self,
        *,
        runner: OmxCommandRunner | None = None,
        latest_commit_resolver=None,
    ) -> None:
        self._runner = runner or OmxCommandRunner()
        self._latest_commit_resolver = latest_commit_resolver or self._fetch_latest_commit

    def detect_status(self, ctx: TargetContext) -> TargetStatus:
        codex_dir = self._codex_dir(ctx)
        if not codex_dir.exists():
            return TargetStatus(
                available=False,
                installed=False,
                enabled=False,
                error="未检测到 Codex，请先安装 Codex。",
            )
        agents_path = codex_dir / "AGENTS.md"
        metadata = {
            "agentsFilePath": str(agents_path),
            "agentsFileExists": agents_path.exists(),
            "backupExists": self._backup_manifest_path(ctx).exists(),
        }
        try:
            package = self._find_installed_package(ctx)
        except RuntimeError as exc:
            return TargetStatus(
                available=False,
                installed=False,
                enabled=False,
                error=str(exc),
                metadata=metadata,
            )
        if package is None:
            return TargetStatus(
                available=True,
                installed=False,
                enabled=False,
                metadata=metadata,
            )
        enabled = self._detect_enabled(codex_dir, package.package_dir)
        return TargetStatus(
            available=True,
            installed=True,
            enabled=enabled,
            version=package.version,
            metadata=metadata,
        )

    def install(self, ctx: TargetContext) -> dict[str, object]:
        return self.install_with_options(ctx, force_agents_overwrite=None)

    def uninstall(self, ctx: TargetContext) -> dict[str, object]:
        package = self._find_installed_package(ctx)
        restored = False
        if package is not None:
            self._run_omx(ctx, package, ["uninstall"])
            restored = self._restore_backup(ctx)
        elif self._backup_manifest_path(ctx).exists():
            restored = self._restore_backup(ctx)
        else:
            raise RuntimeError("oh-my-codex 未安装，请先安装。")
        self._run_npm(ctx, ["uninstall", "-g", OH_MY_CODEX_PACKAGE])
        message = f"已卸载 {OH_MY_CODEX_LABEL}"
        if restored:
            message += "，并恢复原有 Codex 配置"
        return {
            "success": True,
            "message": message,
        }

    def enable(self, ctx: TargetContext) -> dict[str, object]:
        return self.enable_with_options(ctx, force_agents_overwrite=None)

    def disable(self, ctx: TargetContext) -> dict[str, object]:
        package = self._find_installed_package(ctx)
        restored = False
        if package is not None:
            self._run_omx(ctx, package, ["uninstall"])
            restored = self._restore_backup(ctx)
        elif self._backup_manifest_path(ctx).exists():
            restored = self._restore_backup(ctx)
        else:
            raise RuntimeError("oh-my-codex 未安装，请先安装。")
        message = f"已禁用 {OH_MY_CODEX_LABEL}"
        if restored:
            message += "，并恢复原有 Codex 配置"
        return {
            "success": True,
            "message": message,
            "version": package.version if package else None,
        }

    def upgrade(self, ctx: TargetContext) -> dict[str, object]:
        return self.upgrade_with_options(ctx, force_agents_overwrite=None)

    def install_with_options(
        self,
        ctx: TargetContext,
        *,
        force_agents_overwrite: bool | None,
    ) -> dict[str, object]:
        self._ensure_codex_ready(ctx)
        self._require_setup_decision(ctx, force_agents_overwrite)
        self._install_package(ctx)
        package = self._require_package(ctx)
        self._backup_existing_state(ctx)
        self._run_setup(ctx, package, force_agents_overwrite)
        doctor = self._run_doctor_check(ctx, package)
        commit = self._latest_commit_resolver()
        message = f"已安装 {OH_MY_CODEX_LABEL}"
        if doctor["warnings"]:
            message += f"（doctor 发现 {len(doctor['warnings'])} 项非 OK）"
        return {
            "success": True,
            "message": message,
            "version": package.version,
            "commit": commit,
            "doctor": doctor,
            "doctorWarnings": doctor["warnings"],
        }

    def enable_with_options(
        self,
        ctx: TargetContext,
        *,
        force_agents_overwrite: bool | None,
    ) -> dict[str, object]:
        self._ensure_codex_ready(ctx)
        self._require_setup_decision(ctx, force_agents_overwrite)
        package = self._require_package(ctx)
        self._backup_existing_state(ctx)
        self._run_setup(ctx, package, force_agents_overwrite)
        doctor = self._run_doctor_check(ctx, package)
        message = f"已启用 {OH_MY_CODEX_LABEL}"
        if doctor["warnings"]:
            message += f"（doctor 发现 {len(doctor['warnings'])} 项非 OK）"
        return {
            "success": True,
            "message": message,
            "version": package.version,
            "doctor": doctor,
            "doctorWarnings": doctor["warnings"],
        }

    def upgrade_with_options(
        self,
        ctx: TargetContext,
        *,
        force_agents_overwrite: bool | None,
    ) -> dict[str, object]:
        status = self.detect_status(ctx)
        if not status.installed:
            raise RuntimeError("oh-my-codex 未安装，请先安装再升级。")
        was_enabled = status.enabled
        if was_enabled:
            self._require_setup_decision(ctx, force_agents_overwrite)
        self._install_package(ctx)
        package = self._require_package(ctx)
        if was_enabled:
            self._run_setup(ctx, package, force_agents_overwrite)
        commit = self._latest_commit_resolver()
        return {
            "success": True,
            "message": f"已升级 {OH_MY_CODEX_LABEL}",
            "version": package.version,
            "commit": commit,
        }

    def _detect_enabled(self, codex_dir: Path, package_dir: Path) -> bool:
        if _config_contains_omx(codex_dir / "config.toml"):
            return True
        if _hooks_contains_omx(codex_dir / "hooks.json"):
            return True
        if _has_matching_children(codex_dir / "skills", _iter_package_skill_names(package_dir)):
            return True
        if _has_matching_children(codex_dir / "prompts", _iter_package_prompt_names(package_dir)):
            return True
        return False

    def _ensure_codex_ready(self, ctx: TargetContext) -> None:
        codex_dir = self._codex_dir(ctx)
        if not codex_dir.exists():
            raise RuntimeError("未检测到 Codex，请先安装 Codex。")

    def _find_installed_package(self, ctx: TargetContext) -> OmxPackageInfo | None:
        result = self._run_npm(ctx, ["root", "-g"])
        package_root = _normalize_newlines(result.stdout)
        if not package_root:
            return None
        if ctx.environment_id == "wsl":
            if not ctx.wsl_distro:
                raise RuntimeError("未选择 WSL 发行版")
            package_dir = _wsl_path_to_unc(
                ctx.wsl_distro,
                f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}",
            )
            command_dir = f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}"
            entry_script = f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}/dist/cli/omx.js"
        else:
            package_dir = Path(package_root) / OH_MY_CODEX_PACKAGE
            command_dir = str(package_dir)
            entry_script = str(package_dir / "dist" / "cli" / "omx.js")
        if not package_dir.exists():
            return None
        package_json = _read_json(package_dir / "package.json") or {}
        version = str(package_json.get("version") or "").strip() or None
        if not (package_dir / "dist" / "cli" / "omx.js").exists():
            return None
        return OmxPackageInfo(
            package_dir=package_dir,
            version=version,
            entry_script=entry_script,
            command_dir=command_dir,
        )

    def _require_package(self, ctx: TargetContext) -> OmxPackageInfo:
        package = self._find_installed_package(ctx)
        if package is None:
            raise RuntimeError("oh-my-codex 未安装，请先安装。")
        return package

    def _install_package(self, ctx: TargetContext) -> None:
        self._run_npm(ctx, ["install", "-g", OH_MY_CODEX_TARBALL_URL])
        self._prepare_package(ctx)

    def _run_setup(
        self,
        ctx: TargetContext,
        package: OmxPackageInfo,
        force_agents_overwrite: bool | None,
    ) -> subprocess.CompletedProcess[str]:
        args = ["setup"]
        if force_agents_overwrite:
            args.append("--force")
        return self._run_omx(ctx, package, args)

    def _run_doctor_check(
        self,
        ctx: TargetContext,
        package: OmxPackageInfo,
    ) -> dict[str, object]:
        args = ["node", str(package.entry_script), "doctor"]
        try:
            result = self._runner.run(ctx, args, cwd=self._runtime_dir_for(ctx))
        except OSError as exc:
            message = _node_runtime_missing_message(ctx.environment_id)
            return {
                "ran": False,
                "returnCode": None,
                "allOk": False,
                "warnings": [f"[WARN] doctor 未执行: {message} ({exc})"],
                "output": "",
            }

        merged_output = "\n".join(
            part for part in (
                _normalize_newlines(result.stdout),
                _normalize_newlines(result.stderr),
            ) if part
        )
        status_lines = []
        for raw in merged_output.splitlines():
            stripped = raw.strip()
            if stripped.startswith("[") and "]" in stripped:
                status_lines.append(stripped)
        warnings = [line for line in status_lines if not line.startswith("[OK]")]
        if result.returncode != 0 and not warnings:
            detail = _normalize_newlines(result.stderr) or _normalize_newlines(result.stdout) or "doctor 命令执行失败"
            warnings.append(f"[WARN] doctor 返回非 0: {detail}")
        return {
            "ran": True,
            "returnCode": result.returncode,
            "allOk": bool(not warnings),
            "warnings": warnings,
            "output": merged_output,
        }

    def _run_omx(
        self,
        ctx: TargetContext,
        package: OmxPackageInfo,
        omx_args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        args = ["node", str(package.entry_script), *omx_args, "--scope", "user"]
        return self._run(ctx, args)

    def _run_npm(
        self,
        ctx: TargetContext,
        npm_args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        return self._run(ctx, ["npm", *npm_args])

    def _run_npm_in_dir(
        self,
        ctx: TargetContext,
        cwd: str | Path,
        npm_args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        return self._run_with_cwd(ctx, cwd, ["npm", *npm_args])

    def _run(
        self,
        ctx: TargetContext,
        args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        return self._run_with_cwd(ctx, self._runtime_dir_for(ctx), args)

    def _run_with_cwd(
        self,
        ctx: TargetContext,
        cwd: str | Path,
        args: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = self._runner.run(ctx, args, cwd=cwd)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 2 or getattr(exc, "errno", None) == 2:
                raise RuntimeError(_node_runtime_missing_message(ctx.environment_id)) from exc
            raise
        if result.returncode != 0:
            stderr = _normalize_newlines(result.stderr)
            stdout = _normalize_newlines(result.stdout)
            detail = stderr or stdout or "命令执行失败"
            if args and args[0] in {"npm", "node"} and "not found" in detail.lower():
                raise RuntimeError(_node_runtime_missing_message(ctx.environment_id))
            raise RuntimeError(detail)
        return result

    def _prepare_package(self, ctx: TargetContext) -> None:
        package = self._package_from_root(ctx)
        local_entry_script = package.package_dir / "dist" / "cli" / "omx.js"
        if local_entry_script.exists():
            return
        self._run_npm_in_dir(ctx, package.command_dir, ["install", "--include=dev"])
        self._run_npm_in_dir(ctx, package.command_dir, ["run", "build"])
        if not local_entry_script.exists():
            raise RuntimeError(f"oh-my-codex 入口不存在: {local_entry_script}")

    def _package_from_root(self, ctx: TargetContext) -> OmxPackageInfo:
        result = self._run_npm(ctx, ["root", "-g"])
        package_root = _normalize_newlines(result.stdout)
        if not package_root:
            raise RuntimeError("未找到全局 npm 目录。")
        if ctx.environment_id == "wsl":
            if not ctx.wsl_distro:
                raise RuntimeError("未选择 WSL 发行版")
            package_dir = _wsl_path_to_unc(
                ctx.wsl_distro,
                f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}",
            )
            command_dir = f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}"
            entry_script = f"{package_root.rstrip('/')}/{OH_MY_CODEX_PACKAGE}/dist/cli/omx.js"
        else:
            package_dir = Path(package_root) / OH_MY_CODEX_PACKAGE
            command_dir = str(package_dir)
            entry_script = str(package_dir / "dist" / "cli" / "omx.js")
        if not package_dir.exists():
            raise RuntimeError("oh-my-codex 安装目录不存在。")
        package_json = _read_json(package_dir / "package.json") or {}
        version = str(package_json.get("version") or "").strip() or None
        return OmxPackageInfo(
            package_dir=package_dir,
            version=version,
            entry_script=entry_script,
            command_dir=command_dir,
        )

    def _codex_dir(self, ctx: TargetContext) -> Path:
        return Path(ctx.home_dir) / ".codex"

    def _agents_path(self, ctx: TargetContext) -> Path:
        return self._codex_dir(ctx) / "AGENTS.md"

    def _backup_manifest_path(self, ctx: TargetContext) -> Path:
        return _windows_backup_dir(ctx) / "manifest.json"

    def _backup_payload_dir(self, ctx: TargetContext) -> Path:
        return _windows_backup_dir(ctx) / "payload"

    def _agents_requires_confirmation(self, ctx: TargetContext) -> bool:
        return self._agents_path(ctx).exists()

    def _require_setup_decision(
        self,
        ctx: TargetContext,
        force_agents_overwrite: bool | None,
    ) -> None:
        if self._agents_requires_confirmation(ctx) and force_agents_overwrite is None:
            raise RuntimeError("当前目标已存在 AGENTS.md，请先确认是否覆盖后再继续。")

    def _backup_existing_state(self, ctx: TargetContext) -> None:
        codex_dir = self._codex_dir(ctx)
        backup_dir = _windows_backup_dir(ctx)
        payload_dir = self._backup_payload_dir(ctx)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        payload_dir.mkdir(parents=True, exist_ok=True)
        entries: list[dict[str, object]] = []
        for name in OMX_BACKUP_ITEMS:
            source = codex_dir / name
            entry_type = "dir" if source.exists() and source.is_dir() else "file"
            existed = source.exists() or source.is_symlink()
            entries.append({"name": name, "type": entry_type, "existed": existed})
            if existed:
                _copy_path(source, payload_dir / name)
        self._backup_manifest_path(ctx).write_text(
            json.dumps({"entries": entries}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _restore_backup(self, ctx: TargetContext) -> bool:
        manifest_path = self._backup_manifest_path(ctx)
        if not manifest_path.exists():
            return False
        manifest = _read_json(manifest_path)
        if not manifest:
            raise RuntimeError(f"备份清单损坏: {manifest_path}")
        raw_entries = manifest.get("entries")
        if not isinstance(raw_entries, list):
            raise RuntimeError(f"备份清单格式错误: {manifest_path}")
        codex_dir = self._codex_dir(ctx)
        payload_dir = self._backup_payload_dir(ctx)
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                continue
            name = str(raw_entry.get("name") or "").strip()
            if not name:
                continue
            existed = bool(raw_entry.get("existed"))
            target = codex_dir / name
            _remove_path(target)
            if existed:
                source = payload_dir / name
                if not source.exists() and not source.is_symlink():
                    raise RuntimeError(f"备份文件缺失: {source}")
                _copy_path(source, target)
        shutil.rmtree(_windows_backup_dir(ctx))
        return True

    def _runtime_dir_for(self, ctx: TargetContext) -> str | Path:
        if ctx.environment_id == "wsl":
            return _wsl_runtime_dir(ctx)
        return _windows_runtime_dir()

    def _fetch_latest_commit(self) -> str | None:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Invoke-WebRequest -UseBasicParsing 'https://api.github.com/repos/Bjorne1/oh-my-codex/commits/main').Content",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode != 0:
            return None
        try:
            parsed = json.loads(result.stdout)
        except Exception:
            return None
        sha = str(parsed.get("sha") or "").strip()
        return sha or None
