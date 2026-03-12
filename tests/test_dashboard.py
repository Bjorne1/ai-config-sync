import unittest

from python_app.gui.dashboard import STATE_LABELS, summarize_entries


class DashboardSummarizeTests(unittest.TestCase):
    def test_summarize_entries_shows_idle_when_unconfigured_and_undetected(self) -> None:
        state, message = summarize_entries(entries=[], configured_targets={}, detected_targets={})
        self.assertEqual(state, "idle")
        self.assertEqual(message, STATE_LABELS["idle"])

    def test_summarize_entries_marks_detected_when_unconfigured(self) -> None:
        state, message = summarize_entries(
            entries=[],
            configured_targets={},
            detected_targets={"windows": ["codex"]},
        )
        self.assertEqual(state, "idle")
        self.assertEqual(message, "已检测到目标")

    def test_summarize_entries_marks_partial_when_configured_without_status(self) -> None:
        state, message = summarize_entries(
            entries=[],
            configured_targets={"windows": ["codex"]},
            detected_targets={},
        )
        self.assertEqual(state, "partial")
        self.assertEqual(message, "已分配但尚无状态明细")

    def test_summarize_entries_prefixes_environment_and_tool_when_multiple_entries(self) -> None:
        state, message = summarize_entries(
            entries=[
                {
                    "environmentId": "wsl",
                    "toolId": "codex",
                    "state": "conflict",
                    "message": "目标内容与源不一致",
                },
                {
                    "environmentId": "windows",
                    "toolId": "claude",
                    "state": "healthy",
                    "message": "已同步",
                },
            ],
            configured_targets={"windows": ["claude"], "wsl": ["codex"]},
            detected_targets={},
        )
        self.assertEqual(state, "conflict")
        self.assertEqual(message, "WSL/CODEX · 目标内容与源不一致")


if __name__ == "__main__":
    unittest.main()
