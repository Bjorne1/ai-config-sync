from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from abc import ABC, abstractmethod
from .linker import create_symlink, remove_symlink
from dataclasses import dataclass, field
from pathlib import Path


def _rmtree_force(path: Path) -> None:
    """shutil.rmtree with a fallback that clears read-only flags (Windows .git pack files)."""
    def _on_error(_func, file_path, _exc_info):
        os.chmod(file_path, stat.S_IWRITE)
        os.unlink(file_path)
    shutil.rmtree(path, onerror=_on_error)


@dataclass(frozen=True)
class TargetContext:
    environment_id: str
    tool_id: str
    home_dir: str
    wsl_distro: str | None = None


@dataclass(frozen=True)
class TargetStatus:
    available: bool
    installed: bool
    enabled: bool
    version: str | None = None
    installed_commit: str | None = None
    error: str | None = None
    skills_linkable: bool = False
    skills_linked: bool = False
    skills_total: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


class WorkflowHandler(ABC):
    @abstractmethod
    def detect_status(self, ctx: TargetContext) -> TargetStatus: ...

    @abstractmethod
    def install(self, ctx: TargetContext) -> dict[str, object]: ...

    @abstractmethod
    def uninstall(self, ctx: TargetContext) -> dict[str, object]: ...

    @abstractmethod
    def enable(self, ctx: TargetContext) -> dict[str, object]: ...

    @abstractmethod
    def disable(self, ctx: TargetContext) -> dict[str, object]: ...

    @abstractmethod
    def upgrade(self, ctx: TargetContext) -> dict[str, object]: ...

    def workflow_skills_dir(self, ctx: TargetContext) -> Path | None:
        return None

    def tool_skills_dir(self, ctx: TargetContext) -> Path | None:
        return None

    def detect_skills_link_status(
        self, ctx: TargetContext,
    ) -> tuple[bool, bool, int]:
        wf_dir = self.workflow_skills_dir(ctx)
        tool_dir = self.tool_skills_dir(ctx)
        if not wf_dir or not tool_dir or not wf_dir.exists():
            return False, False, 0
        skill_dirs = [d for d in wf_dir.iterdir() if d.is_dir()]
        total = len(skill_dirs)
        if total == 0:
            return False, False, 0
        if not tool_dir.exists():
            return True, False, total
        linked = 0
        for d in skill_dirs:
            target = tool_dir / d.name
            if target.is_symlink():
                try:
                    if target.resolve() == d.resolve():
                        linked += 1
                except OSError:
                    pass
        return True, linked == total, total

    def link_skills(self, ctx: TargetContext) -> dict[str, object]:
        wf_dir = self.workflow_skills_dir(ctx)
        tool_dir = self.tool_skills_dir(ctx)
        if not wf_dir or not tool_dir:
            raise RuntimeError("此工作流不支持 Skill 链接")
        if not wf_dir.exists():
            raise RuntimeError(f"工作流 skills 目录不存在: {wf_dir}")
        tool_dir.mkdir(parents=True, exist_ok=True)
        skill_dirs = [d for d in wf_dir.iterdir() if d.is_dir()]
        created = 0
        skipped = 0
        for d in skill_dirs:
            target = tool_dir / d.name
            if target.is_symlink():
                try:
                    if target.resolve() == d.resolve():
                        skipped += 1
                        continue
                except OSError:
                    pass
                remove_symlink(str(target))
            elif target.exists():
                raise RuntimeError(
                    f"目标已存在且不是软链接: {target}（避免覆盖用户文件）",
                )
            result = create_symlink(str(d), str(target), is_directory=True)
            if result.get("success"):
                created += 1
            elif result.get("permission"):
                raise PermissionError(
                    "创建软链接需要管理员权限或启用开发者模式。\n"
                    "请以管理员身份运行，或在 Windows 设置 → 开发者选项中启用「开发人员模式」。"
                )
            else:
                raise RuntimeError(result.get("message", "创建软链接失败"))
        return {
            "success": True,
            "message": f"已链接 {created} 个 Skills（跳过 {skipped} 个）",
        }

    def unlink_skills(self, ctx: TargetContext) -> dict[str, object]:
        wf_dir = self.workflow_skills_dir(ctx)
        tool_dir = self.tool_skills_dir(ctx)
        if not wf_dir or not tool_dir or not tool_dir.exists():
            return {"success": True, "message": "无需清理"}
        removed = 0
        for entry in tool_dir.iterdir():
            if not entry.is_symlink():
                continue
            try:
                if entry.resolve().is_relative_to(wf_dir.resolve()):
                    result = remove_symlink(str(entry))
                    if result.get("success") and not result.get("skipped"):
                        removed += 1
            except (OSError, ValueError):
                pass
        return {
            "success": True,
            "message": f"已取消链接 {removed} 个 Skills",
        }


# ---------------------------------------------------------------------------
# Claude Code helpers
# ---------------------------------------------------------------------------

SUPERPOWERS_PLUGIN_KEY = "superpowers@superpowers-marketplace"
SUPERPOWERS_MARKETPLACE_REPO = "https://github.com/obra/superpowers-marketplace.git"
SUPERPOWERS_REPO = "https://github.com/obra/superpowers.git"


def _claude_dir(ctx: TargetContext) -> Path:
    return Path(ctx.home_dir) / ".claude"


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _run_git(args: list[str], *, ctx: TargetContext) -> subprocess.CompletedProcess:
    if ctx.wsl_distro:
        cmd_str = " ".join(args)
        return subprocess.run(
            ["wsl.exe", "-d", ctx.wsl_distro, "sh", "-lc", cmd_str],
            capture_output=True, text=True, timeout=120,
        )
    return subprocess.run(args, capture_output=True, text=True, timeout=120)


# ---------------------------------------------------------------------------
# SuperpowersClaudeHandler
# ---------------------------------------------------------------------------


class SuperpowersClaudeHandler(WorkflowHandler):

    def detect_status(self, ctx: TargetContext) -> TargetStatus:
        claude_dir = _claude_dir(ctx)
        if not claude_dir.exists():
            return TargetStatus(available=False, installed=False, enabled=False,
                                error="Claude Code 目录不存在")
        installed_path = claude_dir / "plugins" / "installed_plugins.json"
        installed_data = _read_json(installed_path)
        plugin_entry = None
        version = None
        commit = None
        if isinstance(installed_data, dict):
            plugins = installed_data.get("plugins", {})
            entries = plugins.get(SUPERPOWERS_PLUGIN_KEY)
            if isinstance(entries, list) and entries:
                plugin_entry = entries[0]
                version = str(plugin_entry.get("version") or "")
                commit = str(plugin_entry.get("gitCommitSha") or "")
        is_installed = plugin_entry is not None
        settings_path = claude_dir / "settings.json"
        settings = _read_json(settings_path)
        is_enabled = False
        if isinstance(settings, dict):
            enabled_plugins = settings.get("enabledPlugins", {})
            if isinstance(enabled_plugins, dict):
                is_enabled = bool(enabled_plugins.get(SUPERPOWERS_PLUGIN_KEY))
        return TargetStatus(
            available=True,
            installed=is_installed,
            enabled=is_enabled,
            version=version or None,
            installed_commit=commit or None,
        )

    def enable(self, ctx: TargetContext) -> dict[str, object]:
        return self._set_enabled(ctx, True)

    def disable(self, ctx: TargetContext) -> dict[str, object]:
        return self._set_enabled(ctx, False)

    def _set_enabled(self, ctx: TargetContext, enabled: bool) -> dict[str, object]:
        settings_path = _claude_dir(ctx) / "settings.json"
        settings = _read_json(settings_path) or {}
        enabled_plugins = settings.get("enabledPlugins", {})
        if not isinstance(enabled_plugins, dict):
            enabled_plugins = {}
        enabled_plugins[SUPERPOWERS_PLUGIN_KEY] = enabled
        settings["enabledPlugins"] = enabled_plugins
        _write_json(settings_path, settings)
        action = "启用" if enabled else "禁用"
        return {"success": True, "message": f"已{action} superpowers"}

    def install(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        marketplace_dir = claude_dir / "plugins" / "marketplaces" / "superpowers-marketplace"
        if not marketplace_dir.exists():
            result = _run_git(
                ["git", "clone", SUPERPOWERS_MARKETPLACE_REPO, str(marketplace_dir)],
                ctx=ctx,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone marketplace failed: {result.stderr.strip()}")
        else:
            _run_git(["git", "-C", str(marketplace_dir), "pull", "--ff-only"], ctx=ctx)
        plugin_src = marketplace_dir / "superpowers"
        if not plugin_src.exists():
            raise FileNotFoundError(f"marketplace 中未找到 superpowers 插件: {plugin_src}")
        version = self._detect_version(plugin_src)
        commit = self._detect_commit(marketplace_dir)
        cache_dir = claude_dir / "plugins" / "cache" / "superpowers-marketplace" / "superpowers" / version
        if cache_dir.exists():
            _rmtree_force(cache_dir)
        shutil.copytree(plugin_src, cache_dir)
        self._update_installed_plugins(ctx, cache_dir, version, commit)
        self._update_known_marketplaces(ctx, marketplace_dir)
        self._set_enabled(ctx, True)
        return {
            "success": True,
            "message": f"已安装 superpowers v{version}",
            "version": version,
            "commit": commit,
        }

    def uninstall(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        installed_path = claude_dir / "plugins" / "installed_plugins.json"
        installed_data = _read_json(installed_path)
        if isinstance(installed_data, dict):
            plugins = installed_data.get("plugins", {})
            if isinstance(plugins, dict):
                plugins.pop(SUPERPOWERS_PLUGIN_KEY, None)
                installed_data["plugins"] = plugins
                _write_json(installed_path, installed_data)
        settings_path = claude_dir / "settings.json"
        settings = _read_json(settings_path)
        if isinstance(settings, dict):
            enabled_plugins = settings.get("enabledPlugins", {})
            if isinstance(enabled_plugins, dict):
                enabled_plugins.pop(SUPERPOWERS_PLUGIN_KEY, None)
                settings["enabledPlugins"] = enabled_plugins
                _write_json(settings_path, settings)
        cache_dir = claude_dir / "plugins" / "cache" / "superpowers-marketplace" / "superpowers"
        if cache_dir.exists():
            _rmtree_force(cache_dir)
        return {"success": True, "message": "已卸载 superpowers"}

    def upgrade(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        marketplace_dir = claude_dir / "plugins" / "marketplaces" / "superpowers-marketplace"
        if not marketplace_dir.exists():
            raise RuntimeError("marketplace 仓库不存在，请先安装再升级。")
        result = _run_git(["git", "-C", str(marketplace_dir), "pull", "--ff-only"], ctx=ctx)
        if result.returncode != 0:
            raise RuntimeError(f"git pull marketplace failed: {result.stderr.strip()}")
        plugin_src = marketplace_dir / "superpowers"
        if not plugin_src.exists():
            raise FileNotFoundError(f"marketplace 中未找到 superpowers 插件: {plugin_src}")
        new_version = self._detect_version(plugin_src)
        new_commit = self._detect_commit(marketplace_dir)
        old_status = self.detect_status(ctx)
        cache_parent = claude_dir / "plugins" / "cache" / "superpowers-marketplace" / "superpowers"
        if cache_parent.exists():
            _rmtree_force(cache_parent)
        cache_dir = cache_parent / new_version
        shutil.copytree(plugin_src, cache_dir)
        self._update_installed_plugins(ctx, cache_dir, new_version, new_commit)
        old_ver = old_status.version or "unknown"
        return {
            "success": True,
            "message": f"已升级 superpowers {old_ver} → {new_version}",
            "version": new_version,
            "commit": new_commit,
        }

    def _detect_version(self, plugin_dir: Path) -> str:
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            version = str(data.get("version") or "").strip()
            if version:
                return version
        return "unknown"

    def _detect_commit(self, repo_dir: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _update_installed_plugins(
        self, ctx: TargetContext, install_path: Path, version: str, commit: str,
    ) -> None:
        from datetime import datetime, timezone
        installed_path = _claude_dir(ctx) / "plugins" / "installed_plugins.json"
        data = _read_json(installed_path) or {"version": 2, "plugins": {}}
        plugins = data.get("plugins", {})
        if not isinstance(plugins, dict):
            plugins = {}
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        plugins[SUPERPOWERS_PLUGIN_KEY] = [{
            "scope": "user",
            "installPath": str(install_path),
            "version": version,
            "installedAt": now,
            "lastUpdated": now,
            "gitCommitSha": commit,
        }]
        data["plugins"] = plugins
        _write_json(installed_path, data)

    def _update_known_marketplaces(self, ctx: TargetContext, marketplace_dir: Path) -> None:
        from datetime import datetime, timezone
        km_path = _claude_dir(ctx) / "plugins" / "known_marketplaces.json"
        data = _read_json(km_path) or {}
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        data["superpowers-marketplace"] = {
            "source": {"source": "github", "repo": "obra/superpowers-marketplace"},
            "installLocation": str(marketplace_dir),
            "lastUpdated": now,
        }
        _write_json(km_path, data)


# ---------------------------------------------------------------------------
# SuperpowersCodexHandler
# ---------------------------------------------------------------------------

CODEX_SUPERPOWERS_DIR_NAME = "superpowers"
CODEX_SENTINEL_BEGIN = "<!-- WORKFLOW:superpowers:BEGIN -->"
CODEX_SENTINEL_END = "<!-- WORKFLOW:superpowers:END -->"

CODEX_BOOTSTRAP_BLOCK = f"""{CODEX_SENTINEL_BEGIN}
## Superpowers System

<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>
{CODEX_SENTINEL_END}"""


class SuperpowersCodexHandler(WorkflowHandler):

    def workflow_skills_dir(self, ctx: TargetContext) -> Path | None:
        return Path(ctx.home_dir) / ".codex" / CODEX_SUPERPOWERS_DIR_NAME / "skills"

    def tool_skills_dir(self, ctx: TargetContext) -> Path | None:
        return Path(ctx.home_dir) / ".codex" / "skills"

    def detect_status(self, ctx: TargetContext) -> TargetStatus:
        codex_dir = Path(ctx.home_dir) / ".codex"
        if not codex_dir.exists():
            return TargetStatus(available=False, installed=False, enabled=False,
                                error="Codex 目录不存在")
        sp_dir = codex_dir / CODEX_SUPERPOWERS_DIR_NAME
        is_installed = sp_dir.exists() and sp_dir.is_dir()
        version = None
        commit = None
        if is_installed:
            version = self._detect_version(sp_dir)
            commit = self._detect_commit(sp_dir)
        agents_md = codex_dir / "AGENTS.md"
        is_enabled = self._has_sentinel(agents_md)
        linkable, linked, total = (False, False, 0)
        if is_installed:
            linkable, linked, total = self.detect_skills_link_status(ctx)
        return TargetStatus(
            available=True,
            installed=is_installed,
            enabled=is_enabled,
            version=version,
            installed_commit=commit,
            skills_linkable=linkable,
            skills_linked=linked,
            skills_total=total,
        )

    def install(self, ctx: TargetContext) -> dict[str, object]:
        codex_dir = Path(ctx.home_dir) / ".codex"
        sp_dir = codex_dir / CODEX_SUPERPOWERS_DIR_NAME
        if sp_dir.exists():
            _run_git(["git", "-C", str(sp_dir), "pull", "--ff-only"], ctx=ctx)
        else:
            sp_dir.parent.mkdir(parents=True, exist_ok=True)
            result = _run_git(
                ["git", "clone", SUPERPOWERS_REPO, str(sp_dir)],
                ctx=ctx,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        skills_dir = codex_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        agents_md = codex_dir / "AGENTS.md"
        if not self._has_sentinel(agents_md):
            self._inject_bootstrap(agents_md)
        version = self._detect_version(sp_dir)
        commit = self._detect_commit(sp_dir)
        return {
            "success": True,
            "message": f"已安装 superpowers{f' v{version}' if version else ''}",
            "version": version,
            "commit": commit,
        }

    def uninstall(self, ctx: TargetContext) -> dict[str, object]:
        self.unlink_skills(ctx)
        codex_dir = Path(ctx.home_dir) / ".codex"
        sp_dir = codex_dir / CODEX_SUPERPOWERS_DIR_NAME
        if sp_dir.exists():
            _rmtree_force(sp_dir)
        agents_md = codex_dir / "AGENTS.md"
        self._remove_bootstrap(agents_md)
        return {"success": True, "message": "已卸载 superpowers"}

    def enable(self, ctx: TargetContext) -> dict[str, object]:
        agents_md = Path(ctx.home_dir) / ".codex" / "AGENTS.md"
        if self._has_sentinel(agents_md):
            return {"success": True, "message": "superpowers 已处于启用状态"}
        self._inject_bootstrap(agents_md)
        return {"success": True, "message": "已启用 superpowers"}

    def disable(self, ctx: TargetContext) -> dict[str, object]:
        agents_md = Path(ctx.home_dir) / ".codex" / "AGENTS.md"
        self._remove_bootstrap(agents_md)
        return {"success": True, "message": "已禁用 superpowers"}

    def upgrade(self, ctx: TargetContext) -> dict[str, object]:
        codex_dir = Path(ctx.home_dir) / ".codex"
        sp_dir = codex_dir / CODEX_SUPERPOWERS_DIR_NAME
        if not sp_dir.exists():
            raise RuntimeError("superpowers 未安装，请先安装再升级。")
        old_version = self._detect_version(sp_dir)
        result = _run_git(["git", "-C", str(sp_dir), "pull", "--ff-only"], ctx=ctx)
        if result.returncode != 0:
            raise RuntimeError(f"git pull failed: {result.stderr.strip()}")
        new_version = self._detect_version(sp_dir)
        new_commit = self._detect_commit(sp_dir)
        old_ver = old_version or "unknown"
        new_ver = new_version or "unknown"
        return {
            "success": True,
            "message": f"已升级 superpowers {old_ver} → {new_ver}",
            "version": new_version,
            "commit": new_commit,
        }

    def _has_sentinel(self, agents_md: Path) -> bool:
        if not agents_md.exists():
            return False
        content = agents_md.read_text(encoding="utf-8")
        return CODEX_SENTINEL_BEGIN in content

    def _inject_bootstrap(self, agents_md: Path) -> None:
        agents_md.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        if agents_md.exists():
            existing = agents_md.read_text(encoding="utf-8")
        separator = "\n\n" if existing.strip() else ""
        agents_md.write_text(
            existing.rstrip() + separator + CODEX_BOOTSTRAP_BLOCK + "\n",
            encoding="utf-8",
        )

    def _remove_bootstrap(self, agents_md: Path) -> None:
        if not agents_md.exists():
            return
        content = agents_md.read_text(encoding="utf-8")
        if CODEX_SENTINEL_BEGIN not in content:
            return
        lines = content.split("\n")
        result_lines: list[str] = []
        inside = False
        for line in lines:
            if CODEX_SENTINEL_BEGIN in line:
                inside = True
                continue
            if inside and CODEX_SENTINEL_END in line:
                inside = False
                continue
            if not inside:
                result_lines.append(line)
        cleaned = "\n".join(result_lines).strip()
        agents_md.write_text(cleaned + "\n" if cleaned else "", encoding="utf-8")

    def _detect_version(self, sp_dir: Path) -> str | None:
        release_notes = sp_dir / "RELEASE-NOTES.md"
        if release_notes.exists():
            for line in release_notes.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("## ") and any(c.isdigit() for c in stripped):
                    return stripped.lstrip("# ").strip()
                if stripped.startswith("# ") and any(c.isdigit() for c in stripped):
                    return stripped.lstrip("# ").strip()
        plugin_json = sp_dir / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            version = str(data.get("version") or "").strip()
            if version:
                return version
        return None

    def _detect_commit(self, sp_dir: Path) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(sp_dir), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Agent Skills — constants
# ---------------------------------------------------------------------------

AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIR_NAME = "agent-skills"
AGENT_SKILLS_MANIFEST = ".agent-skills-commands.json"

CODEX_AGENT_SKILLS_DIR_NAME = "agent-skills"
CODEX_AGENT_SKILLS_SENTINEL_BEGIN = "<!-- WORKFLOW:agent-skills:BEGIN -->"
CODEX_AGENT_SKILLS_SENTINEL_END = "<!-- WORKFLOW:agent-skills:END -->"

CODEX_AGENT_SKILLS_BOOTSTRAP = f"""{CODEX_AGENT_SKILLS_SENTINEL_BEGIN}
## Agent Skills System

<EXTREMELY_IMPORTANT>
You have agent-skills installed. Agent Skills provide production-grade engineering workflows
(spec, plan, build, test, review, ship). Before starting any task, check `~/.codex/agent-skills/skills/`
for applicable workflows and follow them step by step.
</EXTREMELY_IMPORTANT>
{CODEX_AGENT_SKILLS_SENTINEL_END}"""


# ---------------------------------------------------------------------------
# AgentSkillsClaudeHandler
# ---------------------------------------------------------------------------


class AgentSkillsClaudeHandler(WorkflowHandler):
    """Manages agent-skills for Claude Code via clone + commands copy."""

    def detect_status(self, ctx: TargetContext) -> TargetStatus:
        claude_dir = _claude_dir(ctx)
        if not claude_dir.exists():
            return TargetStatus(available=False, installed=False, enabled=False,
                                error="Claude Code 目录不存在")
        skills_dir = claude_dir / AGENT_SKILLS_DIR_NAME
        is_installed = skills_dir.exists() and skills_dir.is_dir()
        version = None
        commit = None
        if is_installed:
            version = self._detect_version(skills_dir)
            commit = self._detect_commit(skills_dir)
        is_enabled = self._commands_deployed(claude_dir)
        return TargetStatus(
            available=True,
            installed=is_installed,
            enabled=is_enabled,
            version=version,
            installed_commit=commit,
        )

    def install(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        skills_dir = claude_dir / AGENT_SKILLS_DIR_NAME
        if skills_dir.exists():
            _run_git(["git", "-C", str(skills_dir), "pull", "--ff-only"], ctx=ctx)
        else:
            skills_dir.parent.mkdir(parents=True, exist_ok=True)
            result = _run_git(
                ["git", "clone", AGENT_SKILLS_REPO, str(skills_dir)],
                ctx=ctx,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        self._deploy_commands(claude_dir, skills_dir)
        version = self._detect_version(skills_dir)
        commit = self._detect_commit(skills_dir)
        return {
            "success": True,
            "message": f"已安装 agent-skills{f' v{version}' if version else ''}",
            "version": version,
            "commit": commit,
        }

    def uninstall(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        self._withdraw_commands(claude_dir)
        skills_dir = claude_dir / AGENT_SKILLS_DIR_NAME
        if skills_dir.exists():
            _rmtree_force(skills_dir)
        return {"success": True, "message": "已卸载 agent-skills"}

    def enable(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        skills_dir = claude_dir / AGENT_SKILLS_DIR_NAME
        if not skills_dir.exists():
            raise RuntimeError("agent-skills 未安装，请先安装。")
        self._deploy_commands(claude_dir, skills_dir)
        return {"success": True, "message": "已启用 agent-skills"}

    def disable(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        self._withdraw_commands(claude_dir)
        return {"success": True, "message": "已禁用 agent-skills"}

    def upgrade(self, ctx: TargetContext) -> dict[str, object]:
        claude_dir = _claude_dir(ctx)
        skills_dir = claude_dir / AGENT_SKILLS_DIR_NAME
        if not skills_dir.exists():
            raise RuntimeError("agent-skills 未安装，请先安装再升级。")
        old_version = self._detect_version(skills_dir)
        result = _run_git(["git", "-C", str(skills_dir), "pull", "--ff-only"], ctx=ctx)
        if result.returncode != 0:
            raise RuntimeError(f"git pull failed: {result.stderr.strip()}")
        self._deploy_commands(claude_dir, skills_dir)
        new_version = self._detect_version(skills_dir)
        new_commit = self._detect_commit(skills_dir)
        old_ver = old_version or "unknown"
        new_ver = new_version or "unknown"
        return {
            "success": True,
            "message": f"已升级 agent-skills {old_ver} → {new_ver}",
            "version": new_version,
            "commit": new_commit,
        }

    # -- helpers --

    def _deploy_commands(self, claude_dir: Path, skills_dir: Path) -> None:
        """Copy command .md files from repo .claude/commands/ to ~/.claude/commands/."""
        src_dir = skills_dir / ".claude" / "commands"
        if not src_dir.exists():
            return
        dst_dir = claude_dir / "commands"
        dst_dir.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        for f in sorted(src_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                shutil.copy2(f, dst_dir / f.name)
                copied.append(f.name)
        manifest_path = claude_dir / AGENT_SKILLS_MANIFEST
        _write_json(manifest_path, {"commands": copied})

    def _withdraw_commands(self, claude_dir: Path) -> None:
        """Remove previously deployed command files."""
        manifest_path = claude_dir / AGENT_SKILLS_MANIFEST
        data = _read_json(manifest_path)
        if not isinstance(data, dict):
            return
        commands = data.get("commands", [])
        cmd_dir = claude_dir / "commands"
        for name in commands:
            target = cmd_dir / name
            if target.exists():
                target.unlink()
        if manifest_path.exists():
            manifest_path.unlink()

    def _commands_deployed(self, claude_dir: Path) -> bool:
        manifest_path = claude_dir / AGENT_SKILLS_MANIFEST
        data = _read_json(manifest_path)
        if not isinstance(data, dict):
            return False
        return bool(data.get("commands"))

    def _detect_version(self, skills_dir: Path) -> str | None:
        pkg_json = skills_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                version = str(data.get("version") or "").strip()
                if version:
                    return version
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["git", "-C", str(skills_dir), "describe", "--tags", "--abbrev=0"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _detect_commit(self, skills_dir: Path) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(skills_dir), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# AgentSkillsCodexHandler
# ---------------------------------------------------------------------------


class AgentSkillsCodexHandler(WorkflowHandler):
    """Manages agent-skills for Codex via clone + AGENTS.md injection."""

    def workflow_skills_dir(self, ctx: TargetContext) -> Path | None:
        return Path(ctx.home_dir) / ".codex" / CODEX_AGENT_SKILLS_DIR_NAME / "skills"

    def tool_skills_dir(self, ctx: TargetContext) -> Path | None:
        return Path(ctx.home_dir) / ".codex" / "skills"

    def detect_status(self, ctx: TargetContext) -> TargetStatus:
        codex_dir = Path(ctx.home_dir) / ".codex"
        if not codex_dir.exists():
            return TargetStatus(available=False, installed=False, enabled=False,
                                error="Codex 目录不存在")
        skills_dir = codex_dir / CODEX_AGENT_SKILLS_DIR_NAME
        is_installed = skills_dir.exists() and skills_dir.is_dir()
        version = None
        commit = None
        if is_installed:
            version = self._detect_version(skills_dir)
            commit = self._detect_commit(skills_dir)
        agents_md = codex_dir / "AGENTS.md"
        is_enabled = self._has_sentinel(agents_md)
        linkable, linked, total = (False, False, 0)
        if is_installed:
            linkable, linked, total = self.detect_skills_link_status(ctx)
        return TargetStatus(
            available=True,
            installed=is_installed,
            enabled=is_enabled,
            version=version,
            installed_commit=commit,
            skills_linkable=linkable,
            skills_linked=linked,
            skills_total=total,
        )

    def install(self, ctx: TargetContext) -> dict[str, object]:
        codex_dir = Path(ctx.home_dir) / ".codex"
        skills_dir = codex_dir / CODEX_AGENT_SKILLS_DIR_NAME
        if skills_dir.exists():
            _run_git(["git", "-C", str(skills_dir), "pull", "--ff-only"], ctx=ctx)
        else:
            skills_dir.parent.mkdir(parents=True, exist_ok=True)
            result = _run_git(
                ["git", "clone", AGENT_SKILLS_REPO, str(skills_dir)],
                ctx=ctx,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        agents_md = codex_dir / "AGENTS.md"
        if not self._has_sentinel(agents_md):
            self._inject_bootstrap(agents_md)
        version = self._detect_version(skills_dir)
        commit = self._detect_commit(skills_dir)
        return {
            "success": True,
            "message": f"已安装 agent-skills{f' v{version}' if version else ''}",
            "version": version,
            "commit": commit,
        }

    def uninstall(self, ctx: TargetContext) -> dict[str, object]:
        self.unlink_skills(ctx)
        codex_dir = Path(ctx.home_dir) / ".codex"
        skills_dir = codex_dir / CODEX_AGENT_SKILLS_DIR_NAME
        if skills_dir.exists():
            _rmtree_force(skills_dir)
        agents_md = codex_dir / "AGENTS.md"
        self._remove_bootstrap(agents_md)
        return {"success": True, "message": "已卸载 agent-skills"}

    def enable(self, ctx: TargetContext) -> dict[str, object]:
        agents_md = Path(ctx.home_dir) / ".codex" / "AGENTS.md"
        if self._has_sentinel(agents_md):
            return {"success": True, "message": "agent-skills 已处于启用状态"}
        self._inject_bootstrap(agents_md)
        return {"success": True, "message": "已启用 agent-skills"}

    def disable(self, ctx: TargetContext) -> dict[str, object]:
        agents_md = Path(ctx.home_dir) / ".codex" / "AGENTS.md"
        self._remove_bootstrap(agents_md)
        return {"success": True, "message": "已禁用 agent-skills"}

    def upgrade(self, ctx: TargetContext) -> dict[str, object]:
        codex_dir = Path(ctx.home_dir) / ".codex"
        skills_dir = codex_dir / CODEX_AGENT_SKILLS_DIR_NAME
        if not skills_dir.exists():
            raise RuntimeError("agent-skills 未安装，请先安装再升级。")
        old_version = self._detect_version(skills_dir)
        result = _run_git(["git", "-C", str(skills_dir), "pull", "--ff-only"], ctx=ctx)
        if result.returncode != 0:
            raise RuntimeError(f"git pull failed: {result.stderr.strip()}")
        new_version = self._detect_version(skills_dir)
        new_commit = self._detect_commit(skills_dir)
        old_ver = old_version or "unknown"
        new_ver = new_version or "unknown"
        return {
            "success": True,
            "message": f"已升级 agent-skills {old_ver} → {new_ver}",
            "version": new_version,
            "commit": new_commit,
        }

    # -- helpers --

    def _has_sentinel(self, agents_md: Path) -> bool:
        if not agents_md.exists():
            return False
        content = agents_md.read_text(encoding="utf-8")
        return CODEX_AGENT_SKILLS_SENTINEL_BEGIN in content

    def _inject_bootstrap(self, agents_md: Path) -> None:
        agents_md.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        if agents_md.exists():
            existing = agents_md.read_text(encoding="utf-8")
        separator = "\n\n" if existing.strip() else ""
        agents_md.write_text(
            existing.rstrip() + separator + CODEX_AGENT_SKILLS_BOOTSTRAP + "\n",
            encoding="utf-8",
        )

    def _remove_bootstrap(self, agents_md: Path) -> None:
        if not agents_md.exists():
            return
        content = agents_md.read_text(encoding="utf-8")
        if CODEX_AGENT_SKILLS_SENTINEL_BEGIN not in content:
            return
        lines = content.split("\n")
        result_lines: list[str] = []
        inside = False
        for line in lines:
            if CODEX_AGENT_SKILLS_SENTINEL_BEGIN in line:
                inside = True
                continue
            if inside and CODEX_AGENT_SKILLS_SENTINEL_END in line:
                inside = False
                continue
            if not inside:
                result_lines.append(line)
        cleaned = "\n".join(result_lines).strip()
        agents_md.write_text(cleaned + "\n" if cleaned else "", encoding="utf-8")

    def _detect_version(self, skills_dir: Path) -> str | None:
        pkg_json = skills_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                version = str(data.get("version") or "").strip()
                if version:
                    return version
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["git", "-C", str(skills_dir), "describe", "--tags", "--abbrev=0"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _detect_commit(self, skills_dir: Path) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(skills_dir), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
