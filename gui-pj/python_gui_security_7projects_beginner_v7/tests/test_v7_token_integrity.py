"""Token-by-token exactness of the 696 per-line explanations."""
from pathlib import Path
from bs4 import BeautifulSoup
from collections import Counter
import io
import tokenize
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'

class LexicalCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s=BeautifulSoup(DOC.read_text(encoding='utf8'),'html.parser')
        cls.rows={(int(r['id'].split('-')[2]),int(r['id'].split('-')[3])):r for r in s.select('tr[id^="v6-line-"]')}

    def test_every_token_occurrence_in_same_order(self):
        total=0
        for project in range(1,8):
            src=next((ROOT/'projects').glob(f'{project:02d}_*.py'))
            text=src.read_text(encoding='utf8')
            lines=text.splitlines()
            tokens_by_line={}
            for t in tokenize.generate_tokens(io.StringIO(text).readline):
                if t.type in (tokenize.ENDMARKER,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,tokenize.ENCODING):continue
                tokens_by_line.setdefault(t.start[0],[]).append(t.string if len(t.string)<90 else t.string[:80]+'…')
                total+=1
            for line,raw in enumerate(lines,1):
                row=self.rows.get((project,line))
                if not raw.strip():
                    self.assertIsNone(row);continue
                with self.subTest(project=project,line=line):
                    self.assertIsNotNone(row)
                    self.assertEqual(raw,row.select_one('code.line-source').get_text())
                    actual=[x.get_text() for x in row.select('span.piece > code')]
                    self.assertEqual(tokens_by_line[line],actual)
        self.assertEqual(6504,total)
        self.assertEqual(696,len(self.rows))

    def test_pieces_have_nonempty_japanese_context(self):
        for key,row in self.rows.items():
            for piece in row.select('span.piece'):
                context=piece.find('span')
                with self.subTest(project=key[0],line=key[1]):
                    self.assertIsNotNone(context)
                    self.assertGreaterEqual(len(context.get_text(strip=True)),5)
                    self.assertTrue(context.get_text(strip=True).startswith('：'))

    def test_repeated_equals_and_set_are_not_omitted(self):
        row=self.rows[(1,57)]
        eq=[p for p in row.select('span.piece') if p.find('code').get_text()=='=']
        self.assertEqual(2,len(eq))
        self.assertIn('代入',eq[0].find('span').get_text())
        self.assertIn('キーワード引数',eq[1].find('span').get_text())
        setparts=[p for p in self.rows[(1,22)].select('span.piece') if p.find('code').get_text()=='set']
        self.assertEqual(2,len(setparts))
        self.assertTrue(all('集合' in p.find('span').get_text() for p in setparts))

if __name__=='__main__':unittest.main()
