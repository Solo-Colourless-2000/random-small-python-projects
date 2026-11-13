"""Check 114 prose explanations point at the actual current Python lines."""
import html
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LineExplanationConsistency(unittest.TestCase):
    def test_number_and_code_are_current(self):
        document = (ROOT / "Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html").read_text(encoding="utf-8")
        verified = 0
        for i in range(1, 8):
            section = re.search(
                r'<section\b(?=[^>]*\bid="p%02d")[^>]*>(.*?)</section>' % i,
                document, flags=re.DOTALL)
            self.assertIsNotNone(section, f"Missing project section {i}")
            source = next((ROOT / "projects").glob(f"{i:02d}_*.py"))
            lines = source.read_text(encoding="utf-8").splitlines()
            rows = re.findall(r'<tr\b[^>]*><td>(\d+)</td><td>(.*?)</td><td>(.*?)</td></tr>',
                              section.group(1), flags=re.DOTALL)
            self.assertGreaterEqual(len(rows), 10, f"Too few explanations in project {i}")
            for number_text, source_text, explanation in rows:
                index = int(number_text) - 1
                expected = html.unescape(re.sub(r'<[^>]+>', '', source_text)).strip()
                with self.subTest(project=i, line=number_text, code=expected[:40]):
                    self.assertGreaterEqual(index, 0)
                    self.assertLess(index, len(lines))
                    self.assertEqual(expected, lines[index].strip())
                    self.assertGreater(len(html.unescape(explanation).strip()), 18)
                verified += 1
        self.assertEqual(verified, 136)

    def test_new_detailed_guides_are_located_in_all_projects(self):
        text = (ROOT / "Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html").read_text(encoding="utf-8")
        for i in range(1, 8):
            self.assertIn(f'id="v4-deep-{i:02d}"', text)
            self.assertIn(f'id="v4-deep-title-{i:02d}"', text)
        self.assertIn('id="v4-how-to-read-results"', text)

    def test_no_stale_firewall_behavior_description(self):
        text = (ROOT / "Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html").read_text(encoding="utf-8")
        self.assertNotIn('strict=False', text)
        self.assertIn('strict=True', text)


if __name__ == "__main__":
    unittest.main()
