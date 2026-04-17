import subprocess
import unittest
from unittest import mock

from python_app.core.workflow_handlers import (
    TargetContext,
    _build_git_env,
    _parse_windows_proxy_server,
    _run_git,
)


class WorkflowHandlerProxyTests(unittest.TestCase):
    def test_parse_windows_proxy_server_supports_plain_host_port(self) -> None:
        env = _parse_windows_proxy_server("127.0.0.1:7897")

        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:7897")
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:7897")

    def test_build_git_env_falls_back_to_windows_proxy_settings(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch(
                "python_app.core.workflow_handlers._read_windows_proxy_settings",
                return_value={"HTTP_PROXY": "http://127.0.0.1:7897"},
            ):
                env = _build_git_env()

        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:7897")
        self.assertEqual(env["http_proxy"], "http://127.0.0.1:7897")

    def test_run_git_passes_proxy_env_to_subprocess(self) -> None:
        captured: dict[str, object] = {}

        def _fake_run(args, **kwargs):
            captured["args"] = args
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args, 0, "", "")

        ctx = TargetContext(environment_id="windows", tool_id="claude", home_dir=r"C:\Users\me")
        with mock.patch(
            "python_app.core.workflow_handlers._build_git_env",
            return_value={"HTTP_PROXY": "http://127.0.0.1:7897"},
        ):
            with mock.patch("python_app.core.workflow_handlers.subprocess.run", side_effect=_fake_run):
                _run_git(["git", "status"], ctx=ctx)

        self.assertEqual(captured["args"], ["git", "status"])
        self.assertEqual(captured["env"], {"HTTP_PROXY": "http://127.0.0.1:7897"})


if __name__ == "__main__":
    unittest.main()
