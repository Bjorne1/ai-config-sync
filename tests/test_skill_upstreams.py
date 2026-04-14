import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from python_app.core.github_skill_upstream import (
    derive_child_tree_url,
    infer_skill_name_from_github_url,
    parse_github_tree_url,
    validate_skill_name,
)
from python_app.core.github_skill_upstream import _extract_zip_subpath  # noqa: PLC2701
from python_app.core.skill_upstream_state_service import load_skill_upstreams, save_skill_upstreams


class SkillUpstreamTests(unittest.TestCase):
    def test_validate_skill_name_rejects_path_separators(self) -> None:
        with self.assertRaises(ValueError):
            validate_skill_name("a/b")
        with self.assertRaises(ValueError):
            validate_skill_name(r"a\b")

    def test_parse_github_tree_url_parses_tree_paths(self) -> None:
        ref = parse_github_tree_url("https://github.com/tanweai/pua/tree/main/skills/pua")
        self.assertEqual(ref.owner, "tanweai")
        self.assertEqual(ref.repo, "pua")
        self.assertEqual(ref.ref, "main")
        self.assertEqual(ref.path, "skills/pua")

    def test_derive_child_tree_url_appends_skill_folder(self) -> None:
        derived = derive_child_tree_url("https://github.com/anthropics/skills/tree/main/skills", "pdf")
        self.assertEqual(derived, "https://github.com/anthropics/skills/tree/main/skills/pdf")

    def test_infer_skill_name_from_specific_github_tree_url(self) -> None:
        inferred = infer_skill_name_from_github_url(
            "https://github.com/KKKKhazix/khazix-skills/tree/main/hv-analysis"
        )
        self.assertEqual(inferred, "hv-analysis")

    def test_infer_skill_name_skips_generic_parent_folder(self) -> None:
        inferred = infer_skill_name_from_github_url("https://github.com/anthropics/skills/tree/main/skills")
        self.assertIsNone(inferred)

    def test_extract_zip_subpath_extracts_only_requested_prefix(self) -> None:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("repo-root/skills/pua/SKILL.md", "# pua")
            zip_file.writestr("repo-root/skills/pua/references/a.txt", "a")
            zip_file.writestr("repo-root/skills/other/SKILL.md", "# other")
        zip_bytes = zip_buffer.getvalue()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "out"
            dest.mkdir()
            _extract_zip_subpath(zip_bytes, "skills/pua", dest)
            self.assertTrue((dest / "SKILL.md").exists())
            self.assertTrue((dest / "references" / "a.txt").exists())
            self.assertFalse((dest / "skills" / "other" / "SKILL.md").exists())

    def test_skill_upstream_state_service_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "skill_sources.json"
            saved = save_skill_upstreams(
                {
                    "pua": {"url": "https://github.com/tanweai/pua/tree/main/skills/pua", "installedCommit": "abc"},
                    "bad": {"url": "  "},
                    "demo": "not-a-dict",
                },
                state_file=state_file,
            )
            loaded = load_skill_upstreams(state_file=state_file)
        self.assertEqual(saved, loaded)
        self.assertIn("pua", loaded)
        self.assertNotIn("bad", loaded)
        self.assertNotIn("demo", loaded)


if __name__ == "__main__":
    unittest.main()
