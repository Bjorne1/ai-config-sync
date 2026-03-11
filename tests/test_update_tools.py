import unittest
from unittest.mock import patch

from python_app.core.config_service import normalize_update_tools
from python_app.core.updater import update_all_tools


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


if __name__ == "__main__":
    unittest.main()
