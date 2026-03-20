import tempfile
import unittest
from pathlib import Path

from python_app.core.global_rule_runtime_service import build_global_rule_statuses


def _environment_list(root: Path) -> dict[str, object]:
    return {
        "windows": {
            "id": "windows",
            "roots": {
                "claude": str(root / ".claude"),
                "codex": str(root / ".codex"),
                "gemini": None,
                "antigravity": None,
            },
            "error": None,
        },
        "wsl": {
            "id": "wsl",
            "roots": {
                "claude": str(root / "wsl" / ".claude"),
                "codex": str(root / "wsl" / ".codex"),
                "gemini": str(root / "wsl" / ".gemini"),
                "antigravity": None,
            },
            "error": "未发现 WSL 发行版",
        },
    }


class GlobalRuleRuntimeServiceTests(unittest.TestCase):
    def test_build_global_rule_statuses_covers_core_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".claude").mkdir(parents=True)
            (root / ".codex").mkdir(parents=True)
            (root / ".claude" / "CLAUDE.md").write_text("# same", encoding="utf-8")
            (root / ".codex" / "AGENTS.md").write_text("# old", encoding="utf-8")
            statuses = build_global_rule_statuses(
                {
                    "profiles": [
                        {"id": "rule-1", "name": "规则1", "content": "# same"},
                        {"id": "rule-2", "name": "规则2", "content": "# new"},
                    ],
                    "assignments": {
                        "windows": {"claude": "rule-1", "codex": "rule-2", "gemini": "rule-2"},
                        "wsl": {"claude": "rule-1", "codex": None, "gemini": None},
                    },
                },
                _environment_list(root),
            )
            index = {(item["environmentId"], item["toolId"]): item for item in statuses}

            self.assertEqual(index[("windows", "claude")]["state"], "healthy")
            self.assertEqual(index[("windows", "codex")]["state"], "drifted")
            self.assertEqual(index[("windows", "gemini")]["state"], "tool_unavailable")
            self.assertEqual(index[("wsl", "claude")]["state"], "environment_error")

    def test_build_global_rule_statuses_marks_missing_target_as_outdated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".codex").mkdir(parents=True)
            statuses = build_global_rule_statuses(
                {
                    "profiles": [{"id": "rule-1", "name": "规则1", "content": "# x"}],
                    "assignments": {
                        "windows": {"claude": None, "codex": "rule-1", "gemini": None},
                        "wsl": {"claude": None, "codex": None, "gemini": None},
                    },
                },
                _environment_list(root),
            )
            index = {(item["environmentId"], item["toolId"]): item for item in statuses}
            self.assertEqual(index[("windows", "codex")]["state"], "outdated")


if __name__ == "__main__":
    unittest.main()
