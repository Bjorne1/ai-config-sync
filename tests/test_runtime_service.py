import unittest

from python_app.core import environment_service, runtime_service


class RuntimeServiceTests(unittest.TestCase):
    def test_build_wsl_runtime_uses_default_distro_without_toggle(self) -> None:
        config = {
            "environments": {
                "wsl": {
                    "selectedDistro": None,
                    "targets": {"skills": {}, "commands": {}},
                }
            }
        }
        runtime = runtime_service.build_wsl_runtime(
            config,
            {
                "list_wsl_distros": lambda: ["Ubuntu"],
                "get_default_wsl_distro": lambda: "Ubuntu",
                "get_wsl_home_dir": lambda distro: "/home/wcs",
            },
        )
        self.assertTrue(runtime["available"])
        self.assertEqual(runtime["selectedDistro"], "Ubuntu")
        self.assertEqual(runtime["homeDir"], "/home/wcs")
        self.assertIsNone(runtime["error"])

    def test_list_wsl_distros_strips_utf16_nulls(self) -> None:
        distros = environment_service.list_wsl_distros(
            lambda _args: "U\x00b\x00u\x00n\x00t\x00u\x00\r\n\x00"
        )
        self.assertEqual(distros, ["Ubuntu"])

    def test_get_default_wsl_distro_parses_marked_row(self) -> None:
        output = "  NAME STATE VERSION\r\n* Ubuntu Stopped 2\r\n"
        self.assertEqual(
            environment_service.get_default_wsl_distro(lambda _args: output),
            "Ubuntu",
        )


if __name__ == "__main__":
    unittest.main()
