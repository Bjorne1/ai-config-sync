import json
import tempfile
import unittest
from pathlib import Path

from python_app.core.global_rule_state_service import (
    create_default_global_rule_assignments,
    load_global_rules,
    save_global_rules,
)


class GlobalRuleStateServiceTests(unittest.TestCase):
    def test_load_global_rules_creates_default_state_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = load_global_rules(
                state_file=root / "global_rules.json",
                profile_dir=root / "profiles",
            )

            self.assertEqual(state["profiles"], [])
            self.assertEqual(state["assignments"], create_default_global_rule_assignments())
            self.assertTrue((root / "global_rules.json").exists())
            self.assertTrue((root / "profiles").exists())

    def test_save_global_rules_persists_profiles_and_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = save_global_rules(
                {
                    "profiles": [
                        {
                            "id": "rule-1",
                            "name": "全局规则 1",
                            "content": "# Rule 1\n",
                        }
                    ],
                    "assignments": {
                        "windows": {"claude": "rule-1", "codex": None, "gemini": None},
                        "wsl": {"claude": None, "codex": None, "gemini": None},
                    },
                },
                state_file=root / "global_rules.json",
                profile_dir=root / "profiles",
            )

            self.assertEqual(state["profiles"][0]["file"], "rule-1.md")
            self.assertEqual((root / "profiles" / "rule-1.md").read_text(encoding="utf-8"), "# Rule 1\n")
            manifest = json.loads((root / "global_rules.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["assignments"]["windows"]["claude"], "rule-1")

    def test_load_global_rules_raises_when_profile_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "global_rules.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "profiles": [
                            {
                                "id": "rule-1",
                                "name": "全局规则 1",
                                "file": "rule-1.md",
                                "updatedAt": "2026-03-20T00:00:00",
                            }
                        ],
                        "assignments": create_default_global_rule_assignments(),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "profiles").mkdir()

            with self.assertRaisesRegex(ValueError, "缺少规则版本文件"):
                load_global_rules(
                    state_file=root / "global_rules.json",
                    profile_dir=root / "profiles",
                )


if __name__ == "__main__":
    unittest.main()
