import unittest

from python_app.gui.logo_matrix import MATRIX_GROUPS, TABLE_HEADERS


class LogoMatrixHeaderTests(unittest.TestCase):
    def test_matrix_group_headers_keep_platform_labels(self) -> None:
        self.assertEqual(MATRIX_GROUPS, (("WIN", (3, 4, 5, 6)), ("WSL", (7, 8, 9, 10))))

    def test_tool_headers_are_hidden_when_logos_are_visible(self) -> None:
        self.assertEqual(TABLE_HEADERS[:3], ("选中", "名称", "类型"))
        self.assertTrue(all(header == "" for header in TABLE_HEADERS[3:]))


if __name__ == "__main__":
    unittest.main()
