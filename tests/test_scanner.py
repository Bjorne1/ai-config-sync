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

    def test_expand_commands_flattens_when_subfolders_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command_dir = root / "commit"
            command_dir.mkdir()
            (command_dir / "all.md").write_text("demo", encoding="utf-8")
            commands = scanner.scan_commands(str(root))
            expanded = scanner.expand_commands_for_tool(commands, "codex", False)
        self.assertEqual(expanded[0]["name"], "commit-all.md")


if __name__ == "__main__":
    unittest.main()
