import tempfile
import unittest
from pathlib import Path

from python_app.core.resource_operations import detect_existing_targets
from python_app.core.runtime_service import build_environment_list
from python_app.core.scanner import scan_skills


def _create_config(root: Path) -> dict[str, object]:
    skills_dir = root / "skills"
    commands_dir = root / "commands"
    skills_dir.mkdir()
    commands_dir.mkdir()
    (skills_dir / "demo-skill").mkdir()
    return {
        "version": 3,
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
            "skills": {},
            "commands": {},
        },
        "commandSubfolderSupport": {"default": False, "tools": {"claude": True}},
        "updateTools": {},
    }


class ResourceOperationsTests(unittest.TestCase):
    def test_detect_existing_targets_marks_existing_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = _create_config(root)
            existing_target = root / "targets" / "claude" / "skills" / "demo-skill"
            existing_target.mkdir(parents=True)

            environment_list = build_environment_list(
                config,
                {
                    "list_wsl_distros": lambda: [],
                    "get_default_wsl_distro": lambda: None,
                    "get_wsl_home_dir": lambda distro: None,
                },
            )
            resource = scan_skills(config["sourceDirs"]["skills"])[0]

            detected = detect_existing_targets(config, "skills", resource, environment_list)

        self.assertEqual(detected, {"windows": ["claude"]})


if __name__ == "__main__":
    unittest.main()
