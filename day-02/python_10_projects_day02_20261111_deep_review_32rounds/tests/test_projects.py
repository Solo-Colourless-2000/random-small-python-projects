"""Behavior checks for the supplied reference programs, using only the standard library."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/cases.json").read_text(encoding="ascii"))


class ProjectCases(unittest.TestCase):
    pass


def make_test(spec):
    def test(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            (cwd / "practice").mkdir()
            result = subprocess.run(
                [sys.executable, str(ROOT / "projects" / spec["file"]), *spec["args"]],
                input=spec["stdin"], text=True, encoding="utf-8",
                capture_output=True, cwd=cwd, timeout=5,
            )
            self.assertEqual(result.returncode, spec["status"], result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")
            if spec["expected"] is not None:
                self.assertEqual(result.stdout, spec["expected"])
            if spec["contains"] is not None:
                self.assertIn(spec["contains"], result.stdout)
    return test


for spec in CASES:
    setattr(ProjectCases, "test_" + spec["name"], make_test(spec))


class SourceAndSvgCases(unittest.TestCase):
    def run_svg(self, cwd, output):
        return subprocess.run(
            [sys.executable, str(ROOT / "projects/10_svg_tiles.py"), str(output)],
            text=True, encoding="utf-8", capture_output=True, cwd=cwd, timeout=5,
        )

    def test_all_project_sources_are_ascii(self):
        paths = list((ROOT / "projects").glob("*.py"))
        self.assertEqual(len(paths), 10)
        for path in paths:
            with self.subTest(file=path.name):
                self.assertTrue(path.read_text(encoding="utf-8").isascii())

    def test_svg_geometry_and_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiles.svg"
            result = self.run_svg(directory, path)
            self.assertEqual(result.returncode, 0, result.stdout)
            svg = ET.parse(path).getroot()
            self.assertEqual(svg.attrib["viewBox"], "0 0 240 240")
            rectangles = svg.findall("{http://www.w3.org/2000/svg}rect")
            self.assertEqual(len(rectangles), 17)
            tiles = rectangles[1:]
            self.assertEqual(len({(r.attrib['x'], r.attrib['y']) for r in tiles}), 16)
            self.assertEqual((tiles[0].attrib['x'], tiles[0].attrib['y'], tiles[0].attrib['fill']), ('20','20','#4ec4cc'))
            self.assertEqual((tiles[-1].attrib['x'], tiles[-1].attrib['y'], tiles[-1].attrib['fill']), ('170','170','#e2a0b8'))
            self.assertTrue(all(r.attrib['width'] == '40' and r.attrib['height'] == '40' for r in tiles))

    def test_existing_svg_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiles.svg"
            path.write_text("existing artwork", encoding="ascii")
            result = self.run_svg(directory, path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error: cannot save:", result.stdout)
            self.assertEqual(path.read_text(), "existing artwork")

    def test_missing_parent_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_svg(directory, Path(directory) / "missing/tiles.svg")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Error: cannot save:", result.stdout)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
