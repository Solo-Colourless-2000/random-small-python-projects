"""Independent calculations and regression checks for the revised edition."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
import importlib.util
import io
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "projects").glob("*.py"))
MODULES = []
for index, path in enumerate(FILES):
    spec = importlib.util.spec_from_file_location("project_" + str(index), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    MODULES.append(module)


def run(number, args=(), answers=()):
    stream = io.StringIO()
    values = iter(answers)
    def read(prompt):
        try:
            return next(values)
        except StopIteration:
            raise EOFError from None
    with patch("sys.argv", [FILES[number-1].name, *map(str, args)]), patch("builtins.input", read), redirect_stdout(stream):
        status = MODULES[number-1].main()
    return status, stream.getvalue()


class RevisionCases(unittest.TestCase):
    def test_temperature_boundaries_and_rounding(self):
        for value, expected in [(-100, "-148.0"), (-40,"-40.0"), (0,"32.0"), (100,"212.0")]:
            with self.subTest(value=value):
                self.assertEqual(run(1,answers=[str(value)]),(0,"Fahrenheit: " + expected + " F\n"))
        for value in ["NaN", "-inf", "100.01", "-100.01", ""]:
            self.assertEqual(run(1,answers=[value])[0],2)

    def test_temperature_interrupt(self):
        with patch("builtins.input",side_effect=KeyboardInterrupt), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(MODULES[0].main(),1)
        self.assertEqual(output.getvalue(),"\nConversion stopped.\n")

    def test_bill_distribution_invariants(self):
        for total in [0,1,2,99,1000,10000000]:
            for people in range(1,101):
                status, text=run(2,[total,people])
                lines=text.splitlines()
                high, high_count = lines[0].split(" JPY: ")
                low, low_count = lines[1].split(" JPY: ")
                high=int(high.split()[-1]); low=int(low.split()[-1])
                high_count=int(high_count); low_count=int(low_count)
                self.assertEqual(status,0)
                self.assertEqual(high_count+low_count,people)
                self.assertEqual(high*high_count+low*low_count,total)
                self.assertEqual(high-low,1)
                self.assertGreaterEqual(low_count,1)

    def test_recipe_all_servings(self):
        for servings in range(1,21):
            status,text=run(3,[servings])
            self.assertEqual(status,0)
            values=[float(line.split(": ")[1].split()[0]) for line in text.splitlines()[1:]]
            self.assertEqual(values,[75*servings,100*servings,30*servings])

    def test_dates_valid_and_invalid(self):
        for first,last,expected in [("2026-12-31","2027-01-01","Days remaining: 1"),("2000-02-28","2000-03-01","Days remaining: 2"),("1900-02-28","1900-03-01","Days remaining: 1"),("2026-01-03","2026-01-01","Days since event: 2"),("2026-11-07","2026-11-07","The event is on the reference date.")]:
            self.assertEqual(run(4,[first,last]),(0,expected+"\n"))
        for value in ["2026-2-01","2026/02/01","2026-13-01","0000-01-01","1900-02-29"]:
            self.assertEqual(run(4,[value,"2026-03-01"])[0],2)

    def test_planner_by_integer_minutes(self):
        for hour in range(24):
            for sets in range(1,9):
                status,text=run(5,[f"{hour:02d}:50",sets])
                lines=text.splitlines()
                total=hour*60+50+sets*25+(sets-1)*5
                expected=f"Finish: {(total//60)%24:02d}:{total%60:02d}"
                if total>=1440: expected+=" (next day)"
                self.assertEqual(status,0)
                self.assertEqual(lines[-1],expected)
                self.assertEqual(sum(line.startswith("Break:") for line in lines),sets-1)

    def test_quiz_score_and_normalization(self):
        self.assertIn("Score: 3 / 3",run(6,answers=[" APPLE ","Book"," WATER"])[1])
        self.assertIn("Score: 0 / 3",run(6,answers=["pear","paper","tea"])[1])
        self.assertEqual(run(6,answers=["apple"])[0],1)

    def test_wrap_whitespace_and_width(self):
        self.assertEqual(run(7,[5,"abc def"]),(0,"abc\ndef\nLines: 2\n"))
        self.assertEqual(run(7,[5,"abcdefghijk"]),(0,"abcde\nfghij\nk\nLines: 3\n"))
        self.assertEqual(run(7,[12,"  hello   "]),(0,"hello\nLines: 1\n"))
        self.assertEqual(run(7,[80,"x"*2000])[0],0)
        for args in [[4,"hello"],[81,"hello"],[12," "],[12,"x"*2001]]:
            self.assertEqual(run(7,args)[0],2)

    def test_bars_each_score(self):
        for score in range(101):
            status,text=run(8,[score])
            self.assertEqual(status,0)
            self.assertEqual(text.splitlines()[1].count("#"),score//10)
            self.assertEqual(text.splitlines()[-1],f"Average: {score:.1f}")

    def test_treasure_all_coordinates(self):
        for x in range(1,6):
            for y in range(1,6):
                status,text=run(9,answers=[f"{x} {y}","4 2"])
                self.assertEqual(status,0)
                if (x,y)==(4,2):
                    self.assertIn("Guesses used: 1.",text)
                else:
                    horizontal={-1:"east",0:"same x",1:"west"}[(x>4)-(x<4)]
                    vertical={-1:"north",0:"same y",1:"south"}[(y>2)-(y<2)]
                    self.assertIn(f"Hint: {horizontal} / {vertical}.",text)
                    self.assertIn("Guesses used: 2.",text)
        status,text=run(9,answers=["1 1"]*4+["4 2"])
        self.assertEqual(status,0)
        self.assertIn("Guesses used: 5.",text)

    def test_svg_all_cells_and_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"tiles.SVG"
            self.assertEqual(run(10,[path])[0],0)
            original=path.read_bytes()
            rects=ET.fromstring(original).findall("{http://www.w3.org/2000/svg}rect")[1:]
            colors=["#4ec4cc","#b8e34a","#e2a0b8","#e8a54b"]
            for index,rect in enumerate(rects):
                row,column=divmod(index,4)
                self.assertEqual(rect.attrib["x"],str(20+column*50))
                self.assertEqual(rect.attrib["y"],str(20+row*50))
                self.assertEqual(rect.attrib["fill"],colors[(row+column)%4])
            self.assertEqual(run(10,[path])[0],1)
            self.assertEqual(path.read_bytes(),original)

    def test_all_sources_english_and_importable(self):
        for path in FILES:
            self.assertTrue(path.read_text().isascii())
            compile(path.read_text(),str(path),"exec")


if __name__=="__main__":
    unittest.main()
