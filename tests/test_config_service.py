import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python_app.core import config_service
from python_app.core import resource_state_service


class ConfigServiceTests(unittest.TestCase):
    def test_normalize_resource_map_filters_invalid_tools(self) -> None:
        normalized = config_service.normalize_resource_map(
            {"demo": {"windows": ["claude", "invalid", "claude", "codex"], "wsl": ["gemini", "gemini"]}}
        )
        self.assertEqual(normalized, {"demo": {"windows": ["claude", "codex"], "wsl": ["gemini"]}})

    def test_normalize_resource_map_migrates_legacy_assignments_when_wsl_enabled(self) -> None:
        normalized = config_service.normalize_resource_map(
            {"demo": ["claude", "codex", "claude"]},
            legacy_wsl_enabled=True,
        )
        self.assertEqual(
            normalized,
            {"demo": {"windows": ["claude", "codex"], "wsl": ["claude", "codex"]}},
        )

    def test_load_config_creates_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_file = root / "config.json"
            resources_file = root / "state" / "resources.json"
            with mock.patch.object(config_service, "PROJECT_ROOT", root):
                with mock.patch.object(config_service, "CONFIG_FILE", config_file):
                    with mock.patch.object(resource_state_service, "DEFAULT_RESOURCE_STATE_FILE", resources_file):
                        config = config_service.load_config()
                        self.assertTrue(config_file.exists())
                        self.assertTrue(resources_file.exists())
        self.assertEqual(config["version"], 4)
        self.assertIn("skills", config["sourceDirs"])


if __name__ == "__main__":
    unittest.main()
