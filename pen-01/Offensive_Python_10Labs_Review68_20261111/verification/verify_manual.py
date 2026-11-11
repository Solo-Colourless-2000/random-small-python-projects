"""Offline HTML audit using the Python standard library only."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = sorted((ROOT / "projects").glob("[0-9][0-9]_*.py"))


class ManualParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = []
        self.refs = []
        self.codes = {}
        self.source_lines = {}
        self.steps = self.chapters = self.checks = self.navlinks = self.copy = 0
        self.line_notes = {f"{i:02d}": 0 for i in range(1, 11)}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "section" and "chapter" in classes:
            self.chapters += 1
        if "step" in classes and tag == "article":
            self.steps += 1
        if tag == "input" and "data-check" in attrs:
            self.checks += 1
        if tag == "button" and "copy" in classes:
            self.copy += 1
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.refs.append(attrs["href"][1:])
            if any(item[0] == "nav" for item in self.stack):
                self.navlinks += 1
        if tag == "code" and "id" in attrs:
            self.codes[attrs["id"]] = ""
        if tag == "span" and attrs.get("id", "").startswith("src") and "-L" in attrs["id"]:
            self.source_lines[attrs["id"]] = ""
        if tag == "tr":
            sections = [item[1].get("id", "") for item in self.stack if item[0] == "details"]
            if sections and sections[-1].startswith("source-") and any(item[0] == "tbody" for item in self.stack):
                self.line_notes[sections[-1].split("-")[1]] += 1
        if tag not in self.VOID:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        for tag, attrs in reversed(self.stack):
            if tag == "code" and "id" in attrs:
                self.codes[attrs["id"]] += data
                break
        for tag, attrs in reversed(self.stack):
            if tag == "span" and attrs.get("id", "").startswith("src") and "-L" in attrs["id"]:
                self.source_lines[attrs["id"]] += data
                break


parser = ManualParser()
parser.feed((ROOT / "Python_ペンテスト10作品_全行構文分解_20261111.html").read_text(encoding="utf-8"))
issues = []
checks = 0


def verify(test, message):
    global checks
    checks += 1
    if not test:
        issues.append(message)


verify(parser.chapters == 20, "missing chapters")
verify(parser.steps == 40, "missing steps")
verify(parser.checks == 20, "missing completion checks")
verify(parser.navlinks == 20, "missing navigation links")
verify(parser.copy >= 70, "missing copy controls")
verify(len(parser.ids) == len(set(parser.ids)), "duplicate element ids")
all_ids = set(parser.ids)
for ref in parser.refs:
    verify(ref in all_ids, f"broken link: #{ref}")
for index, path in enumerate(PROJECTS, 1):
    source = path.read_text(encoding="ascii")
    steps = [parser.codes.get(f"p{index:02d}-chunk{step}") for step in range(1, 5)]
    verify(all(step is not None for step in steps), f"missing code chunks: {path.name}")
    verify(''.join(step or '' for step in steps) == source, f"chunks differ from file: {path.name}")
    verify(parser.codes.get(f"src{index:02d}") == source, f"appendix differs from file: {path.name}")
    for number, line in enumerate(source.splitlines(), 1):
        text = parser.source_lines.get(f"src{index:02d}-L{number}")
        verify(text is not None and text.rstrip('\n') == line, f"line {number} differs: {path.name}")
    verify(parser.line_notes[f"{index:02d}"] == sum(bool(line.strip()) for line in source.splitlines()),
           f"not all nonempty source lines explained: {path.name}")
for fixture in ("response_headers.txt", "cookies.txt", "synthetic_traffic.pcap",
                "request_ambiguous.http", "request_simple.http", "webroot/public.txt", "secret.txt"):
    verify((ROOT / "samples" / fixture).exists(), f"missing sample: {fixture}")
for required in ("search", "results", "wrap", "focus", "setup-unzip"):
    verify(required in all_ids, f"missing HTML UI element: {required}")
print(f"HTML_CHECKS={checks}")
print(f"HTML_ERRORS={len(issues)}")
for issue in issues[:30]:
    print("FAIL", issue)
if issues:
    raise SystemExit(1)
print("PASS: snippets, full sources, line notes, 20 chapters, 40 steps, 20 navigation links")
