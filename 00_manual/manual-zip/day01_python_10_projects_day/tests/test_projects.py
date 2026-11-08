"""Basic and negative tests for ten projects using only the standard library."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"


def execute(number, *args):
    scripts = sorted(PROJECTS.glob("*.py"))
    script = scripts[number - 1]
    return subprocess.run(
        [sys.executable, str(script), *[str(item) for item in args]],
        capture_output=True, text=True, check=False,
    )


class MiniProjectsTests(unittest.TestCase):
    def test_01_file_counts(self):
        result = execute(1, ROOT / "samples/downloads")
        self.assertEqual(result.returncode, 0)
        self.assertIn(".txt: 2", result.stdout)
        self.assertIn("Total files: 4", result.stdout)

    def test_01_ignores_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "a.txt").write_text("a")
            (directory / "alias.txt").symlink_to(directory / "a.txt")
            result = execute(1, directory)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Total files: 1", result.stdout)

    def test_01_nonexistent_directory(self):
        self.assertNotEqual(execute(1, "/nonexistent-path-for-mini-python-10").returncode, 0)

    def test_02_keyword_and_line(self):
        result = execute(2, ROOT / "samples/logs/sample.log", "ERROR")
        self.assertEqual(result.returncode, 0)
        self.assertIn("2: ", result.stdout)
        self.assertIn("4: ", result.stdout)
        self.assertIn("Matches: 2", result.stdout)

    def test_02_empty_keyword(self):
        self.assertEqual(execute(2, ROOT / "samples/logs/sample.log", "").returncode, 2)

    def test_02_missing_file(self):
        self.assertNotEqual(execute(2, "missing.log", "ERROR").returncode, 0)

    def test_03_password_length_and_charset(self):
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*")
        for length in (12, 16, 128):
            result = execute(3, length)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(len(result.stdout.strip()), length)
            self.assertTrue(set(result.stdout.strip()) <= allowed)

    def test_03_bad_length(self):
        for length in ("abc", "1", "129"):
            self.assertEqual(execute(3, length).returncode, 2)

    def test_04_sha256_matches_hashlib(self):
        file = ROOT / "samples/downloads/readme.txt"
        expected = hashlib.sha256(file.read_bytes()).hexdigest()
        result = execute(4, file)
        self.assertEqual(result.returncode, 0)
        self.assertIn(expected, result.stdout)

    def test_04_empty_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "empty"
            path.touch()
            result = execute(4, path)
            self.assertEqual(result.returncode, 0)
            self.assertIn(hashlib.sha256(b"").hexdigest(), result.stdout)

    @unittest.skipUnless(os.name == "posix", "POSIX permissions required")
    def test_05_permission_warning(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "demo.txt"
            path.write_text("demo")
            path.chmod(0o666)
            result = execute(5, path)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Permissions: 666", result.stdout)
            self.assertIn("Warning:", result.stdout)
            path.chmod(0o644)
            result = execute(5, path)
            self.assertEqual(result.returncode, 0)
            self.assertIn("OK:", result.stdout)

    def test_05_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "demo"
            path.write_text("content")
            link = Path(root) / "link"
            link.symlink_to(path)
            self.assertNotEqual(execute(5, link).returncode, 0)

    def test_06_match_no_match_ipv6(self):
        self.assertIn("Result: MATCH", execute(6, "192.168.1.20", "192.168.1.0/24").stdout)
        self.assertIn("Result: NO MATCH", execute(6, "192.168.2.20", "192.168.1.0/24").stdout)
        self.assertIn("Result: MATCH", execute(6, "2001:db8::1", "2001:db8::/32").stdout)

    def test_06_invalid_and_mixed(self):
        self.assertEqual(execute(6, "192.168.1.20", "192.168.1.7/24").returncode, 2)
        self.assertEqual(execute(6, "::1", "192.168.1.0/24").returncode, 2)

    def test_07_url_parsed(self):
        result = execute(7, "https://example.com:8443/login?id=10#head")
        self.assertEqual(result.returncode, 0)
        for fragment in ("Scheme: https", "Hostname: example.com", "Port: 8443", "Path: /login", "Query: id=10", "Fragment: head"):
            self.assertIn(fragment, result.stdout)

    def test_07_invalid_port(self):
        self.assertEqual(execute(7, "https://example.com:invalid/").returncode, 2)

    def test_07_missing_scheme(self):
        self.assertEqual(execute(7, "example.com/path").returncode, 2)

    def test_08_csv_counts(self):
        result = execute(8, ROOT / "samples/csv/events.csv")
        self.assertEqual(result.returncode, 0)
        self.assertIn("LOGIN_FAILED: 2", result.stdout)
        self.assertIn("Valid events: 4", result.stdout)
        self.assertIn("Empty event rows: 1", result.stdout)

    def test_08_utf8_bom(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "event.csv"
            file.write_bytes(b"\xef\xbb\xbftime,event\n10:00,ALERT\n")
            result = execute(8, file)
            self.assertEqual(result.returncode, 0)
            self.assertIn("ALERT: 1", result.stdout)

    def test_08_missing_header(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "wrong.csv"
            file.write_text("time,message\n10:00,Hello\n")
            self.assertEqual(execute(8, file).returncode, 2)

    def test_09_json_save_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "system.json"
            result = execute(9, file)
            self.assertEqual(result.returncode, 0)
            data = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"os", "architecture", "python_version"})
            before = file.read_bytes()
            result = execute(9, file)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, file.read_bytes())

    def test_10_zip_contents_and_empty_dir(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            source.mkdir()
            (source / "empty").mkdir()
            (source / "sub").mkdir()
            (source / "sub" / "note.txt").write_text("hello")
            (source / "alias.txt").symlink_to(source / "sub/note.txt")
            target = Path(root) / "backup.zip"
            result = execute(10, source, target)
            self.assertEqual(result.returncode, 0, result.stdout)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.testzip(), None)
                self.assertEqual(archive.read("sub/note.txt"), b"hello")
                self.assertIn("empty/", archive.namelist())
                self.assertNotIn("alias.txt", archive.namelist())
            self.assertNotEqual(execute(10, source, target).returncode, 0)

    def test_10_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            source.mkdir()
            self.assertEqual(execute(10, source, source / "backup.zip").returncode, 2)
            self.assertFalse((source / "backup.zip").exists())

    def test_10_nonexistent_source(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertNotEqual(execute(10, Path(root) / "nope", Path(root) / "backup.zip").returncode, 0)


    def test_01_casefold_no_extension_and_no_recursion(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for filename in ("a.TXT", "b.txt", "README", ".hidden"):
                (directory / filename).write_text("x", encoding="utf-8")
            (directory / "sub").mkdir()
            (directory / "sub" / "deep.txt").write_text("hidden", encoding="utf-8")
            result = execute(1, directory)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(".txt: 2", result.stdout)
            self.assertIn("(no extension): 2", result.stdout)
            self.assertIn("Total files: 4", result.stdout)

    def test_01_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(1, tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Total files: 0", result.stdout)

    def test_02_utf8_and_case_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "log.txt"
            file.write_text("error\nERROR caf\u00e9\nERROR LAST", encoding="utf-8")
            result = execute(2, file, "ERROR")
            self.assertEqual(result.returncode, 0)
            self.assertIn("2: ERROR caf\u00e9", result.stdout)
            self.assertIn("3: ERROR LAST", result.stdout)
            self.assertIn("Matches: 2", result.stdout)
            self.assertNotIn("1: error", result.stdout)

    def test_02_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "raw.log"
            file.write_bytes(b"\xff\xfe")
            result = execute(2, file, "ERROR")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stdout)

    def test_03_no_parameters_and_borders(self):
        self.assertEqual(execute(3).returncode, 2)
        self.assertEqual(execute(3, "12").returncode, 0)
        self.assertEqual(execute(3, "128").returncode, 0)
        self.assertEqual(execute(3, "11").returncode, 2)
        self.assertEqual(execute(3, "129").returncode, 2)

    def test_04_large_file_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "sample.dat"
            data = bytes(range(256)) * 1100
            file.write_bytes(data)
            result = execute(4, file)
            self.assertEqual(result.returncode, 0)
            self.assertIn(hashlib.sha256(data).hexdigest(), result.stdout)
            self.assertEqual(execute(4, Path(tmp) / "missing").returncode, 1)

    @unittest.skipUnless(os.name == "posix", "POSIX only")
    def test_05_permissions_only_others_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "example"
            file.touch()
            for mode, expected in ((0o640, "OK:"), (0o664, "OK:"), (0o622, "Warning:"), (0o777, "Warning:")):
                file.chmod(mode)
                result = execute(5, file)
                self.assertEqual(result.returncode, 0)
                self.assertIn(f"Permissions: {mode:o}", result.stdout)
                self.assertIn(expected, result.stdout)

    def test_05_directory_is_not_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(execute(5, tmp).returncode, 1)

    def test_06_hostbits_and_invalid_address(self):
        self.assertEqual(execute(6, "192.168.1.1", "192.168.1.5/24").returncode, 2)
        self.assertEqual(execute(6, "300.0.0.1", "192.168.1.0/24").returncode, 2)
        self.assertIn("Result: NO MATCH", execute(6, "2001:db9::1", "2001:db8::/32").stdout)

    def test_07_does_not_access_network_and_defaults(self):
        result = execute(7, "http://example.invalid")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Port: (not specified)", result.stdout)
        self.assertIn("Path: /", result.stdout)
        self.assertIn("Query: (none)", result.stdout)
        self.assertEqual(execute(7, "ftp://example.com/").returncode, 2)

    def test_07_out_of_range_port_and_ipv6_host(self):
        self.assertEqual(execute(7, "https://example.com:65536/").returncode, 2)
        result = execute(7, "https://[2001:db8::1]:443/x")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Hostname: 2001:db8::1", result.stdout)
        self.assertIn("Port: 443", result.stdout)

    def test_08_malformed_row_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "events.csv"
            file.write_text("time,event\n10:00,OK\n10:01\n10:02,FAIL,EXTRA\n10:03,\n10:04,OK\n", encoding="utf-8")
            result = execute(8, file)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("OK: 2", result.stdout)
            self.assertIn("Valid events: 2", result.stdout)
            self.assertIn("Empty event rows: 1", result.stdout)
            self.assertIn("Malformed rows: 2", result.stdout)

    def test_08_duplicate_or_empty_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "events.csv"
            for text in ("time,event,event\n1,a,b\n", "time,event,\n1,a,b\n"):
                file.write_text(text, encoding="utf-8")
                result = execute(8, file)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("duplicate or empty", result.stdout)

    def test_08_quoted_comma_and_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "events.csv"
            file.write_bytes(b'time,event\r\n10:00,"ALERT,LOGIN"\r\n10:01,OK\r\n')
            result = execute(8, file)
            self.assertEqual(result.returncode, 0)
            self.assertIn("ALERT,LOGIN: 1", result.stdout)

    def test_08_invalid_quoted_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "events.csv"
            file.write_text('time,event\n10:00,"unterminated\n', encoding="utf-8")
            result = execute(8, file)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stdout)

    def test_09_invalid_output_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(9, Path(tmp) / "missing" / "system.json")
            self.assertEqual(result.returncode, 1)
            self.assertFalse((Path(tmp) / "missing").exists())

    def test_09_output_is_newline_terminated_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "j.json"
            result = execute(9, file)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(file.read_bytes().endswith(b"\n"))
            self.assertIsInstance(json.loads(file.read_text(encoding="utf-8"))["os"], str)

    def test_10_does_not_change_source_or_include_hidden_files_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / ".hidden").write_text("secret", encoding="utf-8")
            (src / "public.txt").write_bytes(b"hello")
            before = {p.name: p.read_bytes() for p in src.iterdir()}
            target = Path(tmp) / "b.zip"
            result = execute(10, src, target)
            self.assertEqual(result.returncode, 0, result.stdout)
            after = {p.name: p.read_bytes() for p in src.iterdir()}
            self.assertEqual(before, after)
            with zipfile.ZipFile(target) as z:
                self.assertIn(".hidden", z.namelist())
                self.assertIn("public.txt", z.namelist())

    def test_10_existing_target_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            target = Path(tmp) / "backup.zip"
            target.write_bytes(b"sentinel")
            result = execute(10, src, target)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(target.read_bytes(), b"sentinel")

    def test_10_nonexistent_parent_and_empty_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            self.assertEqual(execute(10, src, Path(tmp) / "nonexistent" / "backup.zip").returncode, 1)
            target = Path(tmp) / "backup.zip"
            result = execute(10, src, target)
            self.assertEqual(result.returncode, 0)
            with zipfile.ZipFile(target) as z:
                self.assertEqual(z.namelist(), [])

    def test_10_broken_symlink_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "broken").symlink_to(src / "missing")
            target = Path(tmp) / "backup.zip"
            result = execute(10, src, target)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Skipped symlinks: 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
