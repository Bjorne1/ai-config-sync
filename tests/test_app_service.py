import tempfile
import unittest
from pathlib import Path

from python_app.core.app_service import create_app_service


def _create_config(root: Path) -> dict[str, object]:
    skills_dir = root / "skills"
    commands_dir = root / "commands"
    skills_dir.mkdir()
    commands_dir.mkdir()
    (skills_dir / "demo-skill").mkdir()
    (commands_dir / "brainstorming.md").write_text("# test", encoding="utf-8")
    return {
        "version": 2,
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
                "enabled": False,
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
            "skills": {"demo-skill": ["claude"]},
            "commands": {"brainstorming.md": ["codex"]},
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


if __name__ == "__main__":
    unittest.main()
