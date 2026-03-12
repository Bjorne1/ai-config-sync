import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python_app.core import file_sync


class FileSyncCopyTests(unittest.TestCase):
    def test_create_copy_uses_copyfile_for_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.md"
            target_path = root / "target.md"
            source_path.write_text("# hello", encoding="utf-8")

            with mock.patch.object(file_sync.shutil, "copy2", side_effect=AssertionError("copy2 must not be used")):
                result = file_sync.create_copy(str(source_path), str(target_path))

            self.assertTrue(result["success"])
            self.assertEqual(target_path.read_text(encoding="utf-8"), "# hello")

    def test_create_copy_uses_copyfile_for_directories(self) -> None:
        original_copytree = shutil.copytree

        def _copytree_wrapper(*args, **kwargs):
            self.assertIs(kwargs.get("copy_function"), file_sync.shutil.copyfile)
            return original_copytree(*args, **kwargs)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source_dir"
            target_dir = root / "target_dir"
            source_dir.mkdir()
            (source_dir / "a.txt").write_text("a", encoding="utf-8")

            with mock.patch.object(file_sync.shutil, "copytree", side_effect=_copytree_wrapper):
                result = file_sync.create_copy(str(source_dir), str(target_dir))

            self.assertTrue(result["success"])
            self.assertTrue((target_dir / "a.txt").exists())


if __name__ == "__main__":
    unittest.main()
