"""Regression tests for clear failures during path validation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"


def execute(number, path):
    script = next(PROJECTS.glob(f"{number:02}_*.py"))
    args = [sys.executable, str(script), str(path)]
    if number == 2:
        args.append("ERROR")
    return subprocess.run(args, capture_output=True, text=True, check=False)


class PathFailureRegressionTests(unittest.TestCase):
    def assert_explained_failure(self, result):
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error:", result.stdout)
        self.assertEqual(result.stderr, "")

    @unittest.skipUnless(os.name == "posix", "Check POSIX user home expansion")
    def test_unknown_home_user_is_explained(self):
        import pwd

        username = "python_manual_nonexistent_user_987654321"
        try:
            pwd.getpwnam(username)
        except KeyError:
            pass
        else:
            self.skipTest("Test username already exists")
        for number in (1, 2, 4, 5):
            with self.subTest(project=number):
                self.assert_explained_failure(execute(number, f"~{username}/file.txt"))

    @unittest.skipUnless(os.name == "posix", "Check POSIX directory search permissions")
    def test_unsearchable_parent_is_explained(self):
        if os.geteuid() == 0:
            self.skipTest("Mode 000 restriction cannot be tested as root")
        with tempfile.TemporaryDirectory() as temporary:
            locked = Path(temporary) / "locked"
            locked.mkdir()
            (locked / "file.txt").write_text("ERROR\n", encoding="utf-8")
            locked.chmod(0)
            try:
                for number in (1, 2, 4, 5):
                    with self.subTest(project=number):
                        self.assert_explained_failure(execute(number, locked / "file.txt"))
            finally:
                locked.chmod(0o700)

    @unittest.skipUnless(os.name == "posix", "Check POSIX filename length limit")
    def test_overlong_filename_is_explained(self):
        with tempfile.TemporaryDirectory() as temporary:
            maximum = os.pathconf(temporary, "PC_NAME_MAX")
            if maximum <= 0 or maximum > 4096:
                self.skipTest("Filename length limit outside test range")
            path = Path(temporary) / ("a" * (maximum + 1))
            for number in (1, 2, 4, 5):
                with self.subTest(project=number):
                    self.assert_explained_failure(execute(number, path))


if __name__ == "__main__":
    unittest.main()
