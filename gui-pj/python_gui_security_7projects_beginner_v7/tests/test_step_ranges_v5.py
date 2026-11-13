"""All 28 STEP chunks must have accurate source ranges and prose identifiers."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ChunkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=None
        self.codes={}
    def handle_starttag(self, tag, attrs):
        attributes=dict(attrs)
        if tag=='code' and re.fullmatch(r'code-\d\d-[1-4]',attributes.get('id','')):
            self.active=attributes['id']
            self.codes[self.active]=''
    def handle_data(self,data):
        if self.active is not None:
            self.codes[self.active]+=data
    def handle_endtag(self,tag):
        if tag=='code':self.active=None

class StepTests(unittest.TestCase):
    def test_all_captions_follow_real_source(self):
        html=(ROOT/'Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html').read_text(encoding='utf8')
        parser=ChunkParser();parser.feed(html)
        for i in range(1,8):
            source=next((ROOT/'projects').glob(f'{i:02d}_*.py'))
            lines=source.read_text(encoding='utf8').splitlines(keepends=True)
            offset=0
            for j in range(1,5):
                key=f'code-{i:02d}-{j}'
                part=parser.codes[key]
                count=len(part.splitlines(keepends=True))
                start,end=offset+1,offset+count
                self.assertEqual(part,''.join(lines[start-1:end]),key)
                label=f'{source.name} · {start}〜{end}行'
                self.assertIn(f'<span class="file">{label}</span>',html,key)
                self.assertIn(f'aria-label="{label}をコピー"',html,key)
                self.assertIn(f'このSTEPは {start}〜{end} 行です。',html,key)
                offset=end
            self.assertEqual(offset,len(lines))
            self.assertIn(f'id="v5-deep-{i:02d}"',html)

if __name__=='__main__':unittest.main()
