import tempfile
import unittest
from pathlib import Path
from unittest import mock

from python_app.core import config_service


class ConfigServiceTests(unittest.TestCase):
    def test_normalize_resource_map_filters_invalid_tools(self) -> None:
        normalized = config_service.normalize_resource_map(
            {"demo": ["claude", "invalid", "claude", "codex"]}
        )
        self.assertEqual(normalized, {"demo": ["claude", "codex"]})

    def test_load_config_creates_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_file = root / "config.json"
            with mock.patch.object(config_service, "PROJECT_ROOT", root):
                with mock.patch.object(config_service, "CONFIG_FILE", config_file):
                    config = config_service.load_config()
                    self.assertTrue(config_file.exists())
        self.assertEqual(config["version"], 2)
        self.assertIn("skills", config["sourceDirs"])


if __name__ == "__main__":
    unittest.main()
