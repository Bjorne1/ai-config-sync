import tempfile
import unittest
from pathlib import Path

from python_app.core.global_rule_sync_service import sync_global_rules


def _environment_list(root: Path) -> dict[str, object]:
    return {
        "windows": {
            "id": "windows",
            "roots": {
                "claude": str(root / ".claude"),
                "codex": str(root / ".codex"),
                "gemini": str(root / ".gemini"),
                "antigravity": None,
            },
            "error": None,
        },
        "wsl": {
            "id": "wsl",
            "roots": {
                "claude": None,
                "codex": None,
                "gemini": None,
                "antigravity": None,
            },
            "error": "未发现 WSL 发行版",
        },
    }


class GlobalRuleSyncServiceTests(unittest.TestCase):
    def test_sync_global_rules_writes_target_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".codex").mkdir(parents=True)
            results = sync_global_rules(
                {
                    "profiles": [{"id": "rule-1", "name": "规则1", "content": "# sync"}],
                    "assignments": {
                        "windows": {"claude": None, "codex": "rule-1", "gemini": None},
                        "wsl": {"claude": None, "codex": None, "gemini": None},
                    },
                },
                _environment_list(root),
                [{"environmentId": "windows", "toolId": "codex"}],
            )

            self.assertTrue(results[0]["success"])
            self.assertEqual((root / ".codex" / "AGENTS.md").read_text(encoding="utf-8"), "# sync")

    def test_sync_global_rules_skips_unassigned_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".codex").mkdir(parents=True)
            results = sync_global_rules(
                {
                    "profiles": [{"id": "rule-1", "name": "规则1", "content": "# sync"}],
                    "assignments": {
                        "windows": {"claude": None, "codex": None, "gemini": None},
                        "wsl": {"claude": None, "codex": None, "gemini": None},
                    },
                },
                _environment_list(root),
                [{"environmentId": "windows", "toolId": "codex"}],
            )

            self.assertTrue(results[0]["skipped"])
            self.assertIn("未分配规则版本", results[0]["message"])


if __name__ == "__main__":
    unittest.main()
