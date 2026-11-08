"""Regression tests for boundary cases using the standard library."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"


def execute(number, *arguments, environment=None):
    script = next(PROJECTS.glob(f"{number:02}_*.py"))
    return subprocess.run(
        [sys.executable, str(script), *map(str, arguments)],
        capture_output=True, text=True, check=False, env=environment,
    )


class RevisionTests(unittest.TestCase):
    def test_06_network_and_broadcast_are_members(self):
        for address in ("192.168.1.0", "192.168.1.255"):
            result = execute(6, address, "192.168.1.0/24")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Result: MATCH", result.stdout)

    def test_07_userinfo_is_not_hostname(self):
        result = execute(7, "https://user@example.invalid/path")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Hostname: example.invalid", result.stdout)
        self.assertNotIn("Hostname: user", result.stdout)

    def test_08_whitespace_only_header_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "events.csv"
            file.write_text("time,event,   \n10:00,OK,x\n", encoding="utf-8")
            result = execute(8, file)
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicate or empty", result.stdout)

    def test_08_blank_records_and_quoted_newline(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "events.csv"
            file.write_text('time,event\n\n10:00,"MULTI\nLINE"\n10:01, \n', encoding="utf-8")
            result = execute(8, file)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Valid events: 1", result.stdout)
            self.assertIn("Empty event rows: 1", result.stdout)

    @unittest.skipUnless(os.name == "posix", "Check symlinks on POSIX")
    def test_09_dangling_output_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target.json"
            link = Path(temporary) / "alias.json"
            link.symlink_to(target)
            result = execute(9, link)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(target.exists())
            self.assertTrue(link.is_symlink())

    @unittest.skipUnless(os.name == "posix", "Check symlinks on POSIX")
    def test_10_dangling_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / "a.txt").write_text("hello", encoding="utf-8")
            target = Path(temporary) / "target.zip"
            link = Path(temporary) / "alias.zip"
            link.symlink_to(target)
            result = execute(10, source, link)
            self.assertEqual(result.returncode, 1)
            self.assertIn("symbolic link", result.stdout)
            self.assertFalse(target.exists())
            self.assertTrue(link.is_symlink())
            self.assertEqual(result.stderr, "")

    @unittest.skipUnless(os.name == "posix", "Check symlinks on POSIX")
    def test_10_loop_in_output_parent_is_handled(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            loop = Path(temporary) / "loop"
            loop.symlink_to(loop)
            result = execute(10, source, loop / "backup.zip")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_10_pre_1980_timestamp_preserves_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            file = source / "old.txt"
            file.write_bytes(b"old content")
            os.utime(file, (0, 0))
            output = Path(temporary) / "backup.zip"
            result = execute(10, source, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read("old.txt"), b"old content")
                self.assertEqual(archive.getinfo("old.txt").date_time, (1980, 1, 1, 0, 0, 0))
                self.assertIsNone(archive.testzip())

    @unittest.skipUnless(os.name == "posix", "Check symlinks on POSIX")
    def test_10_symlink_directory_is_skipped_without_recursion(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (outside / "excluded.txt").write_text("outside", encoding="utf-8")
            (source / "linked").symlink_to(outside, target_is_directory=True)
            output = Path(temporary) / "backup.zip"
            result = execute(10, source, output)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("Skipped symlinks: 1", result.stdout)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), [])

    @unittest.skipUnless(os.name == "posix" and os.geteuid() != 0, "Check permissions as non-root POSIX user")
    def test_10_unreadable_subdirectory_is_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            hidden = source / "unreadable"
            hidden.mkdir()
            (hidden / "must_not_silently_disappear.txt").write_text("important", encoding="utf-8")
            hidden.chmod(0)
            try:
                result = execute(10, source, Path(temporary) / "backup.zip")
            finally:
                hidden.chmod(0o700)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stdout)
            self.assertNotIn("Saved:", result.stdout)
            self.assertEqual(result.stderr, "")

    @unittest.skipUnless(os.name == "posix", "Check user home expansion on POSIX")
    def test_unknown_home_expansion_is_handled(self):
        unknown = "~__mini_python_no_such_user_7d45b__/data"
        for number, arguments in ((8, (unknown,)), (9, (unknown,)), (10, (unknown, "unused.zip"))):
            result = execute(number, *arguments)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stdout)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
