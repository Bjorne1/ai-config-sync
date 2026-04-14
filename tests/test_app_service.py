import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python_app.core.app_service import create_app_service


def _create_config(root: Path) -> dict[str, object]:
    skills_dir = root / "skills"
    commands_dir = root / "commands"
    skills_dir.mkdir()
    commands_dir.mkdir()
    (skills_dir / "demo-skill").mkdir()
    (commands_dir / "brainstorming.md").write_text("# test", encoding="utf-8")
    return {
        "version": 4,
        "syncMode": "copy",
        "sourceDirs": {
            "skills": str(skills_dir),
            "commands": str(commands_dir),
        },
        "environments": {
            "windows": {
                "enabled": True,
                "targets": {
                    "skills": {
                        "claude": str(root / "targets" / "claude" / "skills"),
                        "codex": str(root / "targets" / "codex" / "skills"),
                        "gemini": str(root / "targets" / "gemini" / "skills"),
                        "antigravity": str(root / "targets" / "ag" / "skills"),
                    },
                    "commands": {
                        "claude": str(root / "targets" / "claude" / "commands"),
                        "codex": str(root / "targets" / "codex" / "prompts"),
                        "gemini": str(root / "targets" / "gemini" / "commands"),
                        "antigravity": str(root / "targets" / "ag" / "workflows"),
                    },
                },
            },
            "wsl": {
                "selectedDistro": None,
                "targets": {
                    "skills": {
                        "claude": "$HOME/.claude/skills",
                        "codex": "$HOME/.codex/skills",
                        "gemini": "$HOME/.gemini/skills",
                        "antigravity": "$HOME/.gemini/antigravity/skills",
                    },
                    "commands": {
                        "claude": "$HOME/.claude/commands",
                        "codex": "$HOME/.codex/prompts",
                        "gemini": "$HOME/.gemini/commands",
                        "antigravity": "$HOME/.gemini/antigravity/global_workflows",
                    },
                },
            },
        },
        "resources": {
            "skills": {"demo-skill": {"windows": ["claude"]}},
            "commands": {"brainstorming.md": {"windows": ["codex"]}},
        },
        "commandSubfolderSupport": {"default": False, "tools": {"claude": True}},
        "updateTools": {"Codex": {"type": "npm", "package": "@openai/codex"}},
    }


class AppServiceTests(unittest.TestCase):
    def test_get_status_returns_scanned_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                }
            )
            status = app_service.get_status()
        self.assertEqual(status["skills"][0]["name"], "demo-skill")
        self.assertEqual(status["commands"][0]["name"], "brainstorming.md")

    def test_sync_resources_accepts_assignment_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            config["resources"]["skills"] = {}
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                }
            )

            result = app_service.sync_resources(
                "skills",
                ["demo-skill"],
                {"demo-skill": {"windows": ["claude"]}},
            )

            target_path = root / "targets" / "claude" / "skills" / "demo-skill"
            self.assertTrue(target_path.exists())
            self.assertEqual(len(result), 1)
            self.assertTrue(result[0]["success"])

    def test_remove_resources_deletes_synced_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            config["resources"]["skills"] = {}
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                }
            )

            app_service.sync_resources("skills", ["demo-skill"], {"demo-skill": {"windows": ["claude"]}})
            target_path = root / "targets" / "claude" / "skills" / "demo-skill"
            self.assertTrue(target_path.exists())

            result = app_service.remove_resources("skills", ["demo-skill"], {"demo-skill": {"windows": ["claude"]}})

            self.assertFalse(target_path.exists())
            self.assertTrue(result)
            self.assertTrue(result[0]["success"])

    def test_add_skill_from_url_does_not_require_specific_skill_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skills_dir = root / "skills"
            commands_dir = root / "commands"
            skills_dir.mkdir()
            commands_dir.mkdir()
            config = {
                "version": 4,
                "syncMode": "copy",
                "sourceDirs": {"skills": str(skills_dir), "commands": str(commands_dir)},
                "environments": {"windows": {"enabled": True, "targets": {}}, "wsl": {"selectedDistro": None, "targets": {}}},
                "resources": {"skills": {}, "commands": {}},
                "commandSubfolderSupport": {"default": False, "tools": {"claude": True}},
                "updateTools": {},
            }
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                    "load_skill_upstreams": lambda: {},
                    "save_skill_upstreams": lambda upstreams: upstreams,
                }
            )

            with mock.patch("python_app.core.app_service.install_github_tree_to_dir", return_value="abc") as installer:
                result = app_service.add_skill_from_url("pua", "https://github.com/tanweai/pua/tree/main/skills")

        self.assertEqual(result["name"], "pua")
        self.assertEqual(result["installedCommit"], "abc")
        installer.assert_called()

    def test_add_skill_from_url_can_infer_name_from_specific_skill_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skills_dir = root / "skills"
            commands_dir = root / "commands"
            skills_dir.mkdir()
            commands_dir.mkdir()
            config = {
                "version": 4,
                "syncMode": "copy",
                "sourceDirs": {"skills": str(skills_dir), "commands": str(commands_dir)},
                "environments": {"windows": {"enabled": True, "targets": {}}, "wsl": {"selectedDistro": None, "targets": {}}},
                "resources": {"skills": {}, "commands": {}},
                "commandSubfolderSupport": {"default": False, "tools": {"claude": True}},
                "updateTools": {},
            }
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                    "load_skill_upstreams": lambda: {},
                    "save_skill_upstreams": lambda upstreams: upstreams,
                }
            )

            with mock.patch("python_app.core.app_service.install_github_tree_to_dir", return_value="abc"):
                result = app_service.add_skill_from_url(
                    "",
                    "https://github.com/KKKKhazix/khazix-skills/tree/main/hv-analysis",
                )

        self.assertEqual(result["name"], "hv-analysis")

    def test_sync_global_rules_uses_current_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            (root / ".codex").mkdir()
            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "load_global_rules": lambda: {
                        "profiles": [{"id": "rule-1", "name": "规则1", "content": "# sync"}],
                        "assignments": {
                            "windows": {"claude": None, "codex": "rule-1", "gemini": None},
                            "wsl": {"claude": None, "codex": None, "gemini": None},
                        },
                    },
                    "save_global_rules": lambda next_state: next_state,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                    "resolve_environment_targets": lambda *_args, **_kwargs: {
                        "windows": {
                            "enabled": True,
                            "targets": config["environments"]["windows"]["targets"],
                            "roots": {
                                "claude": str(root / ".claude"),
                                "codex": str(root / ".codex"),
                                "gemini": str(root / ".gemini"),
                                "antigravity": None,
                            },
                        },
                        "wsl": {
                            "enabled": False,
                            "selectedDistro": None,
                            "targets": {
                                "skills": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                                "commands": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                            },
                            "roots": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                        },
                    },
                }
            )

            result = app_service.sync_global_rules([{"environmentId": "windows", "toolId": "codex"}])

            self.assertTrue(result[0]["success"])
            self.assertEqual((root / ".codex" / "AGENTS.md").read_text(encoding="utf-8"), "# sync")

    def test_sync_global_rules_saves_assignment_override_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            (root / ".codex").mkdir()
            state = {
                "profiles": [{"id": "rule-1", "name": "规则1", "content": "# sync"}],
                "assignments": {
                    "windows": {"claude": None, "codex": None, "gemini": None},
                    "wsl": {"claude": None, "codex": None, "gemini": None},
                },
            }

            def load_global_rules() -> dict[str, object]:
                return state

            def save_global_rules(next_state: dict[str, object]) -> dict[str, object]:
                nonlocal state
                state = next_state
                return next_state

            app_service = create_app_service(
                {
                    "load_config": lambda: config,
                    "save_config": lambda next_config: next_config,
                    "load_global_rules": load_global_rules,
                    "save_global_rules": save_global_rules,
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                    "resolve_environment_targets": lambda *_args, **_kwargs: {
                        "windows": {
                            "enabled": True,
                            "targets": config["environments"]["windows"]["targets"],
                            "roots": {
                                "claude": str(root / ".claude"),
                                "codex": str(root / ".codex"),
                                "gemini": str(root / ".gemini"),
                                "antigravity": None,
                            },
                        },
                        "wsl": {
                            "enabled": False,
                            "selectedDistro": None,
                            "targets": {
                                "skills": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                                "commands": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                            },
                            "roots": {tool_id: None for tool_id in ("claude", "codex", "gemini", "antigravity")},
                        },
                    },
                }
            )

            result = app_service.sync_global_rules(
                [{"environmentId": "windows", "toolId": "codex"}],
                {
                    "windows": {"claude": None, "codex": "rule-1", "gemini": None},
                    "wsl": {"claude": None, "codex": None, "gemini": None},
                },
            )

            self.assertTrue(result[0]["success"])
            self.assertEqual(state["assignments"]["windows"]["codex"], "rule-1")
            self.assertEqual((root / ".codex" / "AGENTS.md").read_text(encoding="utf-8"), "# sync")


if __name__ == "__main__":
    unittest.main()
