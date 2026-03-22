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

            self.assertEqual(state["profiles"][0]["file"], "全局规则 1.md")
            self.assertEqual(
                (root / "profiles" / "全局规则 1.md").read_text(encoding="utf-8"),
                "# Rule 1\n",
            )
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
                                "file": "全局规则 1.md",
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

    def test_save_global_rules_rejects_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "存在重复的规则版本名称"):
                save_global_rules(
                    {
                        "profiles": [
                            {"id": "a", "name": "Same Name", "content": ""},
                            {"id": "b", "name": "Same Name", "content": ""},
                        ],
                        "assignments": create_default_global_rule_assignments(),
                    },
                    state_file=root / "global_rules.json",
                    profile_dir=root / "profiles",
                )

    def test_save_global_rules_renames_file_when_name_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_global_rules(
                {
                    "profiles": [
                        {"id": "r1", "name": "OldName", "content": "hello"},
                    ],
                    "assignments": create_default_global_rule_assignments(),
                },
                state_file=root / "global_rules.json",
                profile_dir=root / "profiles",
            )
            self.assertTrue((root / "profiles" / "OldName.md").exists())

            state = save_global_rules(
                {
                    "profiles": [
                        {"id": "r1", "name": "NewName", "content": "hello"},
                    ],
                    "assignments": create_default_global_rule_assignments(),
                },
                state_file=root / "global_rules.json",
                profile_dir=root / "profiles",
            )

            self.assertTrue((root / "profiles" / "NewName.md").exists())
            self.assertFalse((root / "profiles" / "OldName.md").exists())
            self.assertEqual(state["profiles"][0]["file"], "NewName.md")

    def test_save_global_rules_persists_description(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = save_global_rules(
                {
                    "profiles": [
                        {
                            "id": "r1",
                            "name": "WithDesc",
                            "description": "A test description",
                            "content": "body",
                        },
                    ],
                    "assignments": create_default_global_rule_assignments(),
                },
                state_file=root / "global_rules.json",
                profile_dir=root / "profiles",
            )

            self.assertEqual(state["profiles"][0]["description"], "A test description")
            manifest = json.loads((root / "global_rules.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["profiles"][0]["description"], "A test description",
            )


if __name__ == "__main__":
    unittest.main()
