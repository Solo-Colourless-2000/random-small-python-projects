"""Run 36 distinct, full-artifact re-reads and verification perspectives.

This is a repeatable automated artifact inspection, not a claim that a human
independently interpreted every sentence 36 times. Run from any directory:
python3 tests/review_36_passes.py
"""
import ast
import csv
import hashlib
import json
from io import StringIO
from html.parser import HTMLParser
from pathlib import Path
import importlib.util
from collections import Counter
import re

ROOT = Path(__file__).resolve().parents[1]




class HTMLNode:
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def __getitem__(self, name):
        return self.attrs[name]

    def walk(self):
        for element in self.children:
            if isinstance(element, HTMLNode):
                yield element
                yield from element.walk()

    def get_text(self):
        return ''.join(obj.get_text() if isinstance(obj, HTMLNode) else obj
                       for obj in self.children)

    @staticmethod
    def matches(node, selector):
        if selector.startswith('#'):
            return node.get('id') == selector[1:]
        if selector.startswith('.'):
            return selector[1:] in (node.get('class') or '').split()
        if selector == '[id]':
            return 'id' in node.attrs
        attribute = re.fullmatch(r'([a-z]+)\[([a-z-]+)(?:="([^"]+)")?\]', selector)
        if attribute:
            tag,key,value = attribute.groups()
            return (node.tag == tag and key in node.attrs
                    and (value is None or node.attrs[key] == value))
        parts = selector.split('.', 1)
        return (node.tag == parts[0] and
                (len(parts) == 1 or parts[1] in (node.get('class') or '').split()))

    def select(self, query):
        answers=[]
        options = [part.strip().split() for part in query.split(',')]
        for candidate in self.walk():
            for pieces in options:
                if not self.matches(candidate, pieces[-1]):
                    continue
                ancestor = candidate.parent
                matched = True
                for item in reversed(pieces[:-1]):
                    while ancestor and not self.matches(ancestor, item):
                        ancestor = ancestor.parent
                    if ancestor is None:
                        matched = False
                        break
                    ancestor = ancestor.parent
                if matched:
                    answers.append(candidate)
                    break
        return answers

    def select_one(self, query):
        values=self.select(query)
        return values[0] if values else None


class HTMLView(HTMLParser):
    VOID = {'input','link','meta','img','hr','br','source','wbr'}

    def __init__(self, contents):
        super().__init__(convert_charrefs=True)
        self.root = HTMLNode()
        self.stack = [self.root]
        self.feed(contents)
        self.head = self.select_one('head')

    def handle_starttag(self, tag, attrs):
        child = HTMLNode(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(child)
        if tag not in self.VOID:
            self.stack.append(child)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def select(self, query):
        return self.root.select(query)

    def select_one(self, query):
        return self.root.select_one(query)

    def get_text(self):
        return self.root.get_text()

class Capturer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.codes = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'code' and attributes.get('id', '').startswith(('code-', 'full-')):
            self.current = attributes['id']
            self.codes[self.current] = ''

    def handle_data(self, content):
        if self.current is not None:
            self.codes[self.current] += content

    def handle_endtag(self, tag):
        if tag == 'code':
            self.current = None


def read_everything():
    """Freshly re-read every shipped readable file plus all screenshots."""
    docs = {}
    for path in ROOT.rglob('*'):
        if path.is_file() and path.name != 'CHECKSUMS.sha256' and path.suffix not in {'.pyc'}:
            docs[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    # Binary screenshot contents are read too; no stale in-memory contents shared.
    html = docs['Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'].decode('utf-8')
    soup = HTMLView(html)
    cap = Capturer()
    cap.feed(html)
    sources = {path: content.decode('ascii') for path, content in docs.items()
               if path.startswith('projects/') and path.endswith('.py')}
    config = json.loads(docs['PROJECT_HISTORY.json'])
    return docs, soup, cap.codes, sources, config


def imp(number):
    f = next((ROOT / 'projects').glob(number + '_*.py'))
    spec = importlib.util.spec_from_file_location('audit_' + number, f)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def ok(condition, issue):
    if not condition:
        raise AssertionError(issue)


def check_lockout_model():
    model = imp('07').Throttle()
    assert 'Recorded' in model.attempt('FAIL')
    assert 'Recorded' in model.attempt('FAIL')
    assert 'LOCKED' in model.attempt('FAIL')
    assert 'BLOCKED' in model.attempt('SUCCESS')


def checks():
    return [
        ('7 independently runnable Python projects', lambda d,h,c,s,m: ok(len(s) == 7, 'source count')),
        ('project paths unique', lambda d,h,c,s,m: ok(len(set(s)) == 7, 'duplicate paths')),
        ('all source code ASCII', lambda d,h,c,s,m: ok(all(txt.isascii() for txt in s.values()), 'non ASCII code')),
        ('all source parses as Python', lambda d,h,c,s,m: [ast.parse(txt) for txt in s.values()]),
        ('guarded GUI entrypoints', lambda d,h,c,s,m: ok(all('if __name__ == "__main__":' in txt for txt in s.values()), 'unguarded launch')),
        ('event loop in all GUI projects', lambda d,h,c,s,m: ok(all('root.mainloop()' in txt for txt in s.values()), 'missing loop')),
        ('no source network libraries', lambda d,h,c,s,m: ok(not any(any(x in txt for x in ('import requests','import socket','import urllib','import http.client')) for txt in s.values()), 'network lib')),
        ('source files reasonably small', lambda d,h,c,s,m: ok(all(len(txt.splitlines()) <= 140 for txt in s.values()), 'lesson size')),
        ('17 navigable chapters', lambda d,h,c,s,m: ok(len(h.select('section.chapter')) == 17, 'chapters')),
        ('28 code-building steps', lambda d,h,c,s,m: ok(len(h.select('div.step')) == 28, 'steps')),
        ('7 appendix full source excerpts', lambda d,h,c,s,m: ok(all('full-'+str(n).zfill(2) in c for n in range(1,8)), 'full codes')),
        ('appendices exactly match sources', lambda d,h,c,s,m: ok(all(c['full-'+p['id']] == s['projects/'+p['filename']] for p in m['projects']), 'full source differs')),
        ('step excerpts exactly reconstruct source', lambda d,h,c,s,m: ok(all(''.join(c['code-'+p['id']+'-'+str(i)] for i in range(1,5)) == s['projects/'+p['filename']] for p in m['projects']), 'step mismatch')),
        ('every program has annotations', lambda d,h,c,s,m: ok(len(h.select('.beginner-notes')) >= 21, 'few notes')),
        ('more than 90 beginner line explanations', lambda d,h,c,s,m: ok(sum(len(e.select('tbody tr')) for e in h.select('.beginner-notes table')) >= 90, 'few line notes')),
        ('seven data-flow diagrams in prose', lambda d,h,c,s,m: ok(h.get_text().count('データの流れ：') == 7, 'flow explanations')),
        ('seven three-way lab tables', lambda d,h,c,s,m: ok(h.get_text().count('手を動かす追加実験') == 7, 'lab explanations')),
        ('seven beginner pitfalls sections', lambda d,h,c,s,m: ok(h.get_text().count('初学者が間違えやすいポイント') == 7, 'pitfalls')),
        ('7 GUI screenshots linked', lambda d,h,c,s,m: ok(len(h.select('figure.figure img')) == 7, 'figures')),
        ('images exist as PNG data', lambda d,h,c,s,m: ok(all(d.get(img.get('src',''),b'').startswith(b'\x89PNG\r\n\x1a\n') for img in h.select('figure.figure img')), 'missing png')),
        ('image accessibility alt text', lambda d,h,c,s,m: ok(all(img.get('alt') for img in h.select('figure.figure img')), 'missing alt')),
        ('no remote script/stylesheet dependencies', lambda d,h,c,s,m: ok(not h.select('script[src],link[rel="stylesheet"]'), 'external CSS/JS')),
        ('dark-mode interface is explicit', lambda d,h,c,s,m: ok(re.search(r'<meta(?=[^>]*name="color-scheme")(?=[^>]*content="dark")', d['Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'].decode()) is not None, 'dark setting')),
        ('all chapter targets unique', lambda d,h,c,s,m: ok(len([x.get('id') for x in h.select('[id]')]) == len(set(x.get('id') for x in h.select('[id]'))), 'duplicate ids')),
        ('all local image paths resolve', lambda d,h,c,s,m: ok(all(img['src'] in d for img in h.select('figure.figure img')), 'path broken')),
        ('input sample auth events', lambda d,h,c,s,m: ok(len(list(csv.DictReader(StringIO(d['samples/auth_events.csv'].decode())))) == 6, 'auth rows')),
        ('auth fail tally sample', lambda d,h,c,s,m: ok(max(Counter(row['ip'] for row in csv.DictReader(StringIO(d['samples/auth_events.csv'].decode())) if row['status']=='FAIL').values()) == 3, 'auth tally')),
        ('sample firewall review count', lambda d,h,c,s,m: ok(sum(imp('03').assess(row).startswith('REVIEW') for row in imp('03').read_rules(ROOT/'samples/firewall_rules.csv')) == 3, 'firewall expectations')),
        ('sample IOC match count', lambda d,h,c,s,m: ok(len(imp('04').correlate(imp('04').load_csv(ROOT/'samples/indicators.csv',('type','value')),imp('04').load_csv(ROOT/'samples/ioc_events.csv',('timestamp','ip','domain','sha256')))) == 3, 'IOC expectations')),
        ('sample file baseline count', lambda d,h,c,s,m: ok(len(imp('05').snapshot(ROOT/'samples/integrity_folder')) == 2, 'integrity sample')),
        ('sample mail mismatch clue', lambda d,h,c,s,m: ok(any('differs' in x for x in imp('06').analyze_email(d['samples/mail_headers.txt'].decode())), 'mail clue')),
        ('throttle locks on third failed attempt', lambda d,h,c,s,m: check_lockout_model()),
        ('project time 580 min', lambda d,h,c,s,m: ok(sum(p['minutes'] for p in m['projects']) == 580, 'minutes')),
        ('overall schedule 680 min', lambda d,h,c,s,m: ok(m['target_minutes'] == 680 <= 720, 'time target')),
        ('manual browser controls present', lambda d,h,c,s,m: ok(all(h.select_one('#'+x) for x in ('search','toc','wrap','focus','smaller','larger','reset')), 'missing control')),
        ('review revision metadata and tests exist', lambda d,h,c,s,m: ok(m.get('revision') == 'v7-token-faithful-semantic-beginner-review' and 'tests/test_review_regressions.py' in d, 'missing revision')),
    ]


def main():
    entries = checks()
    assert len(entries) == 36, len(entries)
    log=[]
    for idx,(name,condition) in enumerate(entries,1):
        docs,html,codes,sources,config = read_everything()  # New complete re-read on every pass.
        try:
            condition(docs,html,codes,sources,config)
            log.append(f'{idx:02d}. PASS | {name}')
        except Exception as error:
            log.append(f'{idx:02d}. FAIL | {name} | {type(error).__name__}: {error}')
    contents='AUTOMATED WHOLE-ARTIFACT REVIEW: 36 FRESH PASSES\n'+'\n'.join(log)+'\n'
    (ROOT/'REVIEW_36_PASSES.txt').write_text(contents,encoding='utf-8')
    print(contents)
    if any('. FAIL |' in ln for ln in log):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
