import unittest
from unittest.mock import patch

from python_app.core.config_service import normalize_update_tools
from python_app.core.updater import get_npm_recent_versions, update_all_tools


class UpdateToolsTests(unittest.TestCase):
    def test_normalize_update_tools_keeps_npx_command(self) -> None:
        normalized = normalize_update_tools(
            {
                "Codex Nightly": {
                    "type": "npx",
                    "command": "npx @openai/codex@latest",
                }
            }
        )

        self.assertEqual(
            normalized,
            {
                "Codex Nightly": {
                    "type": "npx",
                    "command": "npx @openai/codex@latest",
                }
            },
        )

    @patch("python_app.core.updater.update_command_tool", return_value=True)
    def test_update_all_tools_runs_npx_command(self, update_command_tool) -> None:
        results = update_all_tools(
            {
                "Codex Nightly": {
                    "type": "npx",
                    "command": "npx @openai/codex@latest",
                }
            }
        )

        update_command_tool.assert_called_once_with("npx @openai/codex@latest")
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[0]["type"], "npx")

    @patch("python_app.core.updater._run_capture")
    def test_get_npm_recent_versions_returns_latest_ten(self, run_capture) -> None:
        run_capture.return_value.stdout = (
            '["1.0.0","1.0.1","1.0.2","1.0.3","1.0.4","1.0.5","1.0.6","1.0.7","1.0.8","1.0.9","1.1.0"]'
        )

        versions = get_npm_recent_versions("@openai/codex", limit=10)

        self.assertEqual(
            versions,
            ["1.1.0", "1.0.9", "1.0.8", "1.0.7", "1.0.6", "1.0.5", "1.0.4", "1.0.3", "1.0.2", "1.0.1"],
        )

    @patch("python_app.core.updater._run_capture")
    def test_get_npm_recent_versions_prefers_stable_versions(self, run_capture) -> None:
        run_capture.return_value.stdout = (
            "["
            "\"0.117.0\","
            "\"0.118.0-alpha.1-win32-x64\","
            "\"0.118.0-alpha.2-win32-x64\","
            "\"0.118.0-alpha.3-win32-x64\""
            "]"
        )

        versions = get_npm_recent_versions("@openai/codex", limit=10)

        self.assertEqual(versions, ["0.117.0"])

    @patch("python_app.core.updater._run_capture")
    def test_get_npm_recent_versions_dedupes_prerelease_core(self, run_capture) -> None:
        run_capture.return_value.stdout = (
            "["
            "\"0.116.0-alpha.2-linux-x64\","
            "\"0.117.0-alpha.5-win32-x64\","
            "\"0.118.0-alpha.1-win32-x64\","
            "\"0.118.0-alpha.2-linux-x64\""
            "]"
        )

        versions = get_npm_recent_versions("@openai/codex", limit=10)

        self.assertEqual(
            versions,
            ["0.118.0-alpha.2-linux-x64", "0.117.0-alpha.5-win32-x64", "0.116.0-alpha.2-linux-x64"],
        )

    @patch("python_app.core.updater.get_npm_version", side_effect=["1.0.0", "1.1.0"])
    @patch("python_app.core.updater.update_npm_tool", return_value=True)
    def test_update_all_tools_uses_target_version(self, update_npm_tool, _get_npm_version) -> None:
        results = update_all_tools(
            {
                "Codex": {
                    "type": "npm",
                    "package": "@openai/codex",
                }
            },
            target_versions={"Codex": "1.1.0"},
        )

        update_npm_tool.assert_called_once_with("@openai/codex", "1.1.0")
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[0]["targetVersion"], "1.1.0")


if __name__ == "__main__":
    unittest.main()
