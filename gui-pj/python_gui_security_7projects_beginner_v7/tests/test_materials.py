"""Check that the delivered guide matches the delivered Python files."""
from html.parser import HTMLParser
from pathlib import Path
import ast
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceCodeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = None
        self.codes = {}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "code" and attr.get("id", "").startswith(("full-", "code-")):
            self.capture = attr["id"]
            self.codes[self.capture] = ""

    def handle_data(self, data):
        if self.capture:
            self.codes[self.capture] += data

    def handle_endtag(self, tag):
        if tag == "code":
            self.capture = None


class ManualConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html").read_text(encoding="utf-8")
        cls.parser = SourceCodeParser()
        cls.parser.feed(cls.html)
        cls.config = json.loads((ROOT / "PROJECT_HISTORY.json").read_text(encoding="utf-8"))

    def test_seven_independent_sources(self):
        self.assertEqual(len(list((ROOT / "projects").glob("*.py"))), 7)
        self.assertEqual(len(self.config["projects"]), 7)

    def test_time_budget(self):
        self.assertEqual(self.config["target_minutes"], 680)
        self.assertLessEqual(self.config["target_minutes"], 720)
        self.assertEqual(sum(row["minutes"] for row in self.config["projects"]), 580)

    def test_full_source_exactly_matches(self):
        for item in self.config["projects"]:
            with self.subTest(id=item["id"]):
                code = (ROOT / "projects" / item["filename"]).read_text(encoding="utf-8")
                self.assertEqual(self.parser.codes["full-" + item["id"]], code)

    def test_step_source_exactly_matches(self):
        for item in self.config["projects"]:
            with self.subTest(id=item["id"]):
                chunks = [text for name, text in sorted(self.parser.codes.items())
                          if name.startswith("code-" + item["id"] + "-")]
                self.assertGreaterEqual(len(chunks), 3)
                self.assertEqual("".join(chunks), (ROOT / "projects" / item["filename"]).read_text(encoding="utf-8"))

    def test_python_source_ascii_and_ast(self):
        for file in (ROOT / "projects").glob("*.py"):
            with self.subTest(file=file.name):
                contents = file.read_text(encoding="utf-8")
                self.assertTrue(contents.isascii())
                ast.parse(contents)

    def test_images_and_basic_ui_controls(self):
        self.assertEqual(self.html.count('<section class="chapter"'), 17)
        self.assertEqual(self.html.count('<figure class="figure">'), 7)
        self.assertEqual(len(list((ROOT / "images").glob("*.png"))), 7)
        for attr in ('id="search"', 'id="toc"', 'id="wrap"',
                     'id="focus"', 'id="smaller"', 'id="larger"',
                     'id="reset"', 'id="current"'):
            self.assertIn(attr, self.html)

    def test_required_samples_exist(self):
        for name in ("auth_events.csv", "response_headers.txt", "firewall_rules.csv",
                     "indicators.csv", "ioc_events.csv", "mail_headers.txt",
                     "integrity_folder/config.txt", "integrity_folder/readme.txt"):
            self.assertTrue((ROOT / "samples" / name).is_file())


if __name__ == "__main__":
    unittest.main()
