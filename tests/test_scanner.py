import tempfile
import unittest
from pathlib import Path

from python_app.core import scanner


class ScannerTests(unittest.TestCase):
    def test_scan_skills_returns_files_and_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "alpha").mkdir()
            (root / "beta.md").write_text("demo", encoding="utf-8")
            (root / ".gitkeep").write_text("", encoding="utf-8")
            skills = scanner.scan_skills(str(root))
        names = [item["name"] for item in skills]
        self.assertEqual(names, ["alpha", "beta.md"])

    def test_scan_skills_extracts_description_from_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "brainstorming_tool"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: brainstorming_tool\ndescription: Hello World\n---\n",
                encoding="utf-8",
            )
            skills = scanner.scan_skills(str(root))
        self.assertEqual(skills[0]["description"], "Hello World")
        self.assertEqual(skills[0]["descriptionSource"], "frontmatter")

    def test_expand_commands_flattens_when_subfolders_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command_dir = root / "commit"
            command_dir.mkdir()
            (command_dir / "all.md").write_text("demo", encoding="utf-8")
            commands = scanner.scan_commands(str(root))
            expanded = scanner.expand_commands_for_tool(commands, "codex", False)
        self.assertEqual(expanded[0]["name"], "commit-all.md")

    def test_scan_commands_uses_frontmatter_description_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "task.md").write_text("---\ndescription: demo command\n---\n# Title\n", encoding="utf-8")
            commands = scanner.scan_commands(str(root))
        self.assertEqual(commands[0]["description"], "demo command")
        self.assertEqual(commands[0]["descriptionSource"], "frontmatter")

    def test_scan_commands_falls_back_to_first_30_chars_when_missing_description(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "task.md").write_text("# Title\nThis is a command without meta.\n", encoding="utf-8")
            commands = scanner.scan_commands(str(root))
        self.assertEqual(commands[0]["description"], "# Title This is a command with")
        self.assertEqual(commands[0]["descriptionSource"], "content")


if __name__ == "__main__":
    unittest.main()
