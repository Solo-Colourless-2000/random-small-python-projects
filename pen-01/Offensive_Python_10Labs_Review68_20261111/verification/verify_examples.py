"""Independently replay published examples in small groups."""
import html
import re
import sys
from pathlib import Path
from build_manual import DATA, observed

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / 'Python_ペンテスト10作品_全行構文分解_20261111.html'
GROUPS = {"1": (1, 2, 3), "2": (4, 5, 6), "3": (7, 8), "4": (9, 10)}


def main():
    if len(sys.argv) == 1:
        selected = range(1, 11)
    elif len(sys.argv) == 2 and sys.argv[1] in GROUPS:
        selected = GROUPS[sys.argv[1]]
    else:
        print('Usage: python3 verification/verify_examples.py [1|2|3|4]')
        return 2
    document = PAGE.read_text(encoding='utf-8')
    issues = []
    for n in selected:
        out, err, status = observed(DATA[n - 1]['cmd'])
        if n == 3:
            out = re.sub(r'Local demo port: \d+', 'Local demo port: （実行時にOSが割り当てた番号）', out)
        match = re.search(r'<code id="out-%02d"[^>]*>(.*?)</code>' % n, document, flags=re.DOTALL)
        shown = html.unescape(match.group(1)) if match else None
        if shown != out or err or status not in (0, 1):
            issues.append(f'Lab {n:02d}: shown/observed stdout or exit mismatch')
    print(f'EXAMPLE_OUTPUT_CHECKS={len(list(selected))} ERRORS={len(issues)}')
    for issue in issues:
        print('FAIL:', issue)
    if issues:
        return 1
    print('PASS: displayed output matches newly executed commands')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
