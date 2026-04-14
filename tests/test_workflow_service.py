import unittest
from unittest import mock

from python_app.core.workflow_handlers import TargetStatus
from python_app.core.workflow_registry import WorkflowDefinition
from python_app.core.workflow_service import execute_workflow_action


class RecordingWorkflowHandler:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def detect_status(self, _ctx):
        return TargetStatus(available=True, installed=False, enabled=False)

    def install(self, _ctx):
        raise AssertionError("install should not be used when install_with_options is available")

    def install_with_options(self, ctx, *, force_agents_overwrite, supplement_rules):
        self.calls.append(("install", force_agents_overwrite, supplement_rules))
        return {"success": True, "commit": "abc", "version": "1.0.0"}

    def uninstall(self, _ctx):
        return {"success": True}

    def enable(self, _ctx):
        return {"success": True}

    def disable(self, _ctx):
        return {"success": True}

    def upgrade(self, _ctx):
        return {"success": True}

    def link_skills(self, _ctx):
        return {"success": True}

    def unlink_skills(self, _ctx):
        return {"success": True}


class WorkflowServiceTests(unittest.TestCase):
    def test_execute_workflow_action_passes_omx_options(self) -> None:
        handler = RecordingWorkflowHandler()
        environments = {
            "windows": {
                "roots": {"codex": r"C:\Users\me\.codex"},
                "error": None,
            }
        }
        saved_states: list[dict[str, object]] = []
        definition = WorkflowDefinition(
            workflow_id="oh-my-codex",
            label="oh-my-codex",
            description="test",
            repo_url="https://example.com",
            supported_tools=("codex",),
            handler_factory=lambda _tool_id: handler,
        )

        with mock.patch.dict(
            "python_app.core.workflow_service.WORKFLOW_REGISTRY",
            {"oh-my-codex": definition},
            clear=True,
        ):
            result = execute_workflow_action(
                "oh-my-codex",
                "windows:codex",
                "install|force=1|supplement=1",
                environments,
                {},
                lambda state: saved_states.append(state),
            )

        self.assertTrue(result["success"])
        self.assertEqual(handler.calls, [("install", True, True)])
        self.assertEqual(saved_states[0]["oh-my-codex"]["targets"]["windows:codex"]["installedVersion"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
