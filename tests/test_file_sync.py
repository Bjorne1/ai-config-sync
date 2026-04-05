import subprocess
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

            with mock.patch.object(file_sync.shutil, "copy2", wraps=shutil.copy2) as copy2_mock:
                result = file_sync.create_copy(str(source_path), str(target_path))

            self.assertTrue(result["success"])
            self.assertTrue(copy2_mock.called)
            self.assertEqual(target_path.read_text(encoding="utf-8"), "# hello")

    def test_create_copy_uses_copyfile_for_directories(self) -> None:
        original_copytree = shutil.copytree

        def _copytree_wrapper(*args, **kwargs):
            self.assertIs(kwargs.get("copy_function"), file_sync.shutil.copy2)
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


class FileSyncRemoveTests(unittest.TestCase):
    def test_remove_path_unlinks_when_entry_is_dangling_link(self) -> None:
        with (
            mock.patch.object(file_sync, "has_path", return_value=True),
            mock.patch.object(file_sync.os.path, "exists", return_value=False),
            mock.patch.object(file_sync.os.path, "islink", return_value=False),
            mock.patch.object(file_sync.Path, "unlink", autospec=True) as unlink_mock,
            mock.patch.object(file_sync.shutil, "rmtree") as rmtree_mock,
        ):
            result = file_sync.remove_path(r"C:\demo\link")

        self.assertTrue(result["success"])
        self.assertEqual(unlink_mock.call_count, 1)
        rmtree_mock.assert_not_called()

    def test_remove_path_prefers_unlink_for_directory_link_shape(self) -> None:
        with (
            mock.patch.object(file_sync, "has_path", return_value=True),
            mock.patch.object(file_sync.os.path, "exists", return_value=True),
            mock.patch.object(file_sync.os.path, "islink", return_value=False),
            mock.patch.object(file_sync.Path, "is_file", return_value=False),
            mock.patch.object(file_sync.Path, "is_dir", return_value=True),
            mock.patch.object(file_sync.Path, "unlink", autospec=True) as unlink_mock,
            mock.patch.object(file_sync.os, "rmdir") as rmdir_mock,
            mock.patch.object(file_sync.shutil, "rmtree") as rmtree_mock,
        ):
            result = file_sync.remove_path(r"C:\demo\dir_link")

        self.assertTrue(result["success"])
        self.assertEqual(unlink_mock.call_count, 1)
        rmdir_mock.assert_not_called()
        rmtree_mock.assert_not_called()

    def test_remove_path_uses_wsl_delete_for_unc_targets(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="__OK__\n",
            stderr="",
        )
        with (
            mock.patch.object(file_sync, "has_path", return_value=True),
            mock.patch.object(file_sync.subprocess, "run", return_value=completed) as run_mock,
            mock.patch.object(file_sync.Path, "unlink", autospec=True) as unlink_mock,
        ):
            result = file_sync.remove_path(r"\\wsl.localhost\Ubuntu\home\wcs\.codex\skills\demo")

        self.assertTrue(result["success"])
        unlink_mock.assert_not_called()
        self.assertEqual(run_mock.call_count, 1)

    def test_remove_path_wsl_delete_returns_skipped_when_missing(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="__MISSING__\n",
            stderr="",
        )
        with mock.patch.object(file_sync.subprocess, "run", return_value=completed):
            result = file_sync.remove_path(r"\\wsl.localhost\Ubuntu\home\wcs\.codex\skills\demo")
        self.assertTrue(result["success"])
        self.assertTrue(result["skipped"])


if __name__ == "__main__":
    unittest.main()
