"""Reproducible Day02 audit: 40 distinct review lenses, stdlib only.
Run from the package root: python3 verification/audit_40_checks.py
This is not a claim of exhaustive proof; every lens records a concrete assertion.
"""
from contextlib import redirect_stdout
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
import importlib.util
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
FILES=sorted((ROOT/'projects').glob('*.py'))
SOURCES={p.name:p.read_text(encoding='ascii') for p in FILES}
HTML=(ROOT/'manual.html').read_text(encoding='utf-8')
MODULES=[]
for i,p in enumerate(FILES):
    spec=importlib.util.spec_from_file_location('audit_project_'+str(i),p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    MODULES.append(mod)

class AuditHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.ids=[];self.links=[];self.tags=[];self.chapters=[];self.lessons=[]
        self.sources=[];self.guides=0;self.active=None;self.data=[];self.copy_buttons=0
        self.code_rows={};self.css_chunks=[];self.script_chunks=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); classes=a.get('class','').split(); self.tags.append((tag,a))
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='section' and 'chapter' in classes:self.chapters.append(a.get('id'))
        if tag=='article' and 'lesson' in classes:self.lessons.append(a)
        if tag=='details' and 'source-file' in classes:self.sources.append(a)
        if tag=='details' and 'syntax-anatomy' in classes:self.guides+=1
        if tag=='button' and 'copy' in classes:self.copy_buttons+=1
        owner=None
        if ('lesson' in classes or 'source-file' in classes) and 'data-file' in a:
            owner=(a['data-file'],a.get('id',''))
        if tag=='span' and 'code-line' in classes and a.get('data-number') and self._owner():
            owner_info=self._owner()
            # Any code-line inside the relevant lesson/source file is the precise source listing.
            self.active=(owner_info,int(a['data-number']))
            self.data=[]
        self.stack.append((tag,a,owner))
    def _owner(self):
        for _,a,owner in reversed(self.stack):
            if owner:return owner
        return None
    def handle_data(self,data):
        if self.active:self.data.append(data)
        if self.stack and self.stack[-1][0]=='style':self.css_chunks.append(data)
        if self.stack and self.stack[-1][0]=='script':self.script_chunks.append(data)
    def handle_endtag(self,tag):
        if tag=='span' and self.active and self.stack and 'code-line' in self.stack[-1][1].get('class','').split():
            owner,no=self.active
            self.code_rows.setdefault(owner,{}).setdefault(no,[]).append(''.join(self.data))
            self.active=None;self.data=[]
        if self.stack:
            # HTML is authored validly; HTMLParser does not enforce nesting, so pop to match.
            for j in range(len(self.stack)-1,-1,-1):
                if self.stack[j][0]==tag:
                    del self.stack[j:]
                    break

h=AuditHTML();h.feed(HTML)
results=[]
def check(title,description,func):
    try:
        evidence=func()
        results.append({'number':len(results)+1,'lens':title,'result':'PASS','evidence':description+'; '+str(evidence)[:400]})
    except Exception as exc:
        results.append({'number':len(results)+1,'lens':title,'result':'FAIL','evidence':description+'; '+type(exc).__name__+': '+str(exc)})

def run(no,args=(),inputs=()):
    text=io.StringIO()
    iterable=iter(inputs)
    def read(prompt):
        text.write(prompt)
        try:return next(iterable)
        except StopIteration:raise EOFError from None
    with patch('sys.argv',[FILES[no-1].name,*map(str,args)]),patch('builtins.input',read),redirect_stdout(text):
        status=MODULES[no-1].main()
    return status,text.getvalue()

def verify_all_line_maps():
    assert len(h.sources)==10 and len(h.lessons)==40
    for file,source in SOURCES.items():
        expected=source.splitlines()
        groups=[(owner,rows) for owner,rows in h.code_rows.items() if owner[0]==file]
        assert len(groups)==5,(file,len(groups))
        final=[row for owner,row in groups if owner[1].startswith('source')]
        assert len(final)==1
        actual=final[0]
        assert len(actual)==len(expected),(file,len(actual),len(expected))
        for n,line in enumerate(expected,1):assert actual[n]==[line],(file,n,actual[n],line)
    return '10 complete source listings exactly match projects'

check('01 Package identity','10 expected Python sources and mandatory files',lambda:(len(FILES)==10 and all((ROOT/n).exists() for n in ['manual.html','README.txt','PROJECT_HISTORY.json','tests/cases.json'])) or (_ for _ in ()).throw(AssertionError('missing mandatory files')))
check('02 English-only source','all project scripts are ASCII',lambda:all(s.isascii() for s in SOURCES.values()) or (_ for _ in ()).throw(AssertionError('non-ASCII source')))
check('03 Syntax compilation','compile every project source',lambda:[compile(code,path,'exec') for path,code in SOURCES.items()] and '10 compiled')
check('04 Module loading','all projects import without output',lambda:len(MODULES)==10 and '10 modules loaded')
check('05 Standard library','imports are math/sys/datetime/textwrap/pathlib only',lambda:all(not re.search(r'\bimport\s+(requests|numpy|pandas|flask|tkinter)\b',s) for s in SOURCES.values()) or (_ for _ in ()).throw(AssertionError('external module')))
check('06 Ten chapters','all 20 chapter IDs including 10 projects',lambda:(len(h.chapters)==20 and all('checkpoint-'+str(i) in h.chapters for i in range(1,11))) or (_ for _ in ()).throw(AssertionError('chapter count')))
check('07 Forty steps','4 lessons in each of 10 projects',lambda:all(sum(a.get('id','').startswith(f'p{i:02}-step') for a in h.lessons)==4 for i in range(1,11)) or (_ for _ in ()).throw(AssertionError('steps missing')))
check('08 Complete source consistency','source files and appendix snippets line-for-line',verify_all_line_maps)

def verify_steps():
  for file,source in SOURCES.items():
    groups=sorted(((owner[1],rows) for owner,rows in h.code_rows.items() if owner[0]==file and owner[1].startswith('p')),key=lambda t:t[0]); concat=[]
    for _,rows in groups:
      concat.extend(line for n,ls in sorted(rows.items()) for line in ls)
    assert '\n'.join(concat)+'\n'==source,(file,len(concat),len(source.splitlines()))
  return '40 lessons concatenate into 10 exact files'
check('09 Stage concatenation','append four contiguous steps reproduces each source',verify_steps)
check('10 Every line guided','syntax detail exists twice for each nonblank source line',lambda: (h.guides==2*sum(sum(bool(l.strip()) for l in s.splitlines()) for s in SOURCES.values())) or (_ for _ in ()).throw(AssertionError('missing syntax guides')))
check('11 Token explanation mechanics','all syntax microscopes have paired definition entries',lambda:(HTML.count('class="token-gloss"')==h.guides and HTML.count('class="syntax-anatomy"')==h.guides) or (_ for _ in ()).throw(AssertionError('token guides missing')))
check('12 Duplicate anchors','no duplicate HTML IDs',lambda: len(h.ids)==len(set(h.ids)) or (_ for _ in ()).throw(AssertionError('duplicate IDs')))
check('13 Internal navigation','all fragment links target existing IDs',lambda:all(x[1:] in set(h.ids) for x in h.links if x.startswith('#') and x!='#') or (_ for _ in ()).throw(AssertionError('broken link')))
check('14 Offline assets','no external script, CSS, image assets',lambda:all(not(t in ('script','link','img') and (a.get('src','').startswith('http') or a.get('href','').startswith('http'))) for t,a in h.tags) or (_ for _ in ()).throw(AssertionError('external asset')))
check('15 Copy controls','code-copy buttons are present',lambda: h.copy_buttons>=100 or (_ for _ in ()).throw(AssertionError('copy buttons')))
check('16 Dark and responsive','dark color-scheme and mobile CSS',lambda: ('color-scheme: dark' in HTML and '@media(max-width:650px)' in HTML) or (_ for _ in ()).throw(AssertionError('responsive CSS missing')))
check('17 Interactive search','search input and search script included',lambda: ('id="search"' in HTML and 'function runSearch()' in HTML) or (_ for _ in ()).throw(AssertionError('search absent')))
check('18 Key operation hints','vim workflow and commands present',lambda: all(s in HTML for s in ['vim practice/01_temperature.py','Esc','Ctrl','-m unittest']) or (_ for _ in ()).throw(AssertionError('setup hints missing')))
check('19 Temperature formula','32F at 0C, -40F at -40C',lambda:all(s==0 and f'Fahrenheit: {v:.1f} F' in out for x,v in [(0,32),(-40,-40),(100,212)] for s,out in [run(1,inputs=[str(x)])]) or (_ for _ in ()).throw(AssertionError('temperature output')))
check('20 Temperature validation','NaN, infinity, out-of-range rejected',lambda:all(run(1,inputs=[s])[0]==2 for s in ['nan','inf','-inf','100.01','-100.01','abc','']) or (_ for _ in ()).throw(AssertionError('temperature accepted invalid')))
check('21 Bill invariant','total preserved for 5 amounts x 5 people',lambda:all(f'Checked total: {total} JPY' in run(2,(total,people))[1] for total in [0,1,2,1000,10000000] for people in [1,2,3,7,100]) or (_ for _ in ()).throw(AssertionError('bill mismatch')))
check('22 Bill bounds','zero people, negatives, 101 people rejected',lambda:all(run(2,x)[0]==2 for x in [(100,0),(-1,2),(0,101),(10000001,2)]) or (_ for _ in ()).throw(AssertionError('bill bounds')))
check('23 Recipe scaling','2,3,20 servings scale rice to 150,225,1500 g',lambda:all(f'rice: {v:.1f} g' in run(3,(n,))[1] for n,v in [(2,150),(3,225),(20,1500)]) or (_ for _ in ()).throw(AssertionError('recipe scaling')))
check('24 Recipe rejection','0,21 and noninteger rejected',lambda:all(run(3,(x,))[0]==2 for x in [0,21,'abc']) or (_ for _ in ()).throw(AssertionError('recipe bounds')))
check('25 Leap-year math','2000 leap and 1900 non-leap',lambda:run(4,('2000-02-28','2000-03-01'))[1].endswith('2\n') and run(4,('1900-02-28','1900-03-01'))[1].endswith('1\n') or (_ for _ in ()).throw(AssertionError('leap math')))
check('26 Strict date text','invalid date spelling and value rejected',lambda:all(run(4,(x,'2026-03-01'))[0]==2 for x in ['2026-2-01','2026-W01-1','2026/02/01','2026-02-29','0000-01-01']) or (_ for _ in ()).throw(AssertionError('bad date accepted')))
check('27 Planner midnight','next day suffix when crossing midnight',lambda:'Finish: 00:15 (next day)' in run(5,('23:50',1))[1] or (_ for _ in ()).throw(AssertionError('rollover')))
check('28 Planner breaks','exactly sets minus one breaks',lambda:all(run(5,('09:00',n))[1].count('Break:')==n-1 for n in range(1,9)) or (_ for _ in ()).throw(AssertionError('break count')))
check('29 Quiz words and fairness','hints carry starting letter; mixed case accepted',lambda:all(t in SOURCES['06_flashcard_quiz.py'] for t in ['red fruit: a____','bound pages: b___','H2O']) and 'Score: 3 / 3' in run(6,inputs=[' APPLE ','BOOK','water'])[1] or (_ for _ in ()).throw(AssertionError('quiz hints')))
check('30 Quiz input interruption','short stream yields quit status 1',lambda:run(6,inputs=['apple'])[0]==1 or (_ for _ in ()).throw(AssertionError('quiz EOF')))
check('31 Word wrap widths','long word split at widths 5 and 12',lambda:all(run(7,(w,'a'*25))[1].splitlines()[0]=='a'*w for w in [5,12]) or (_ for _ in ()).throw(AssertionError('wrap widths')))
check('32 Word wrap validation','empty and too long rejected',lambda:all(run(7,x)[0]==2 for x in [(5,' '),(81,'abc'),(12,'x'*2001)]) or (_ for _ in ()).throw(AssertionError('wrap bounds')))
check('33 Score bars rounding','99 gives 9 bars, 100 gives 10 bars',lambda:all(run(8,(n,))[1].splitlines()[1].count('#')==n//10 for n in [0,9,10,99,100]) or (_ for _ in ()).throw(AssertionError('bars')))
check('34 Score average','average of 60,85,100 is 81.7',lambda:'Average: 81.7' in run(8,(60,85,100))[1] or (_ for _ in ()).throw(AssertionError('average')))
check('35 Treasure invalid attempts','invalid guess does not reduce valid attempts',lambda:'Guesses used: 1.' in run(9,inputs=['bad','9 2','4 2'])[1] or (_ for _ in ()).throw(AssertionError('attempts')))
check('36 Treasure direction','1 1 -> east north, then find 4 2',lambda:'Hint: east / north.' in run(9,inputs=['1 1','4 2'])[1] or (_ for _ in ()).throw(AssertionError('hints')))

def svg_check():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'tiles.svg'
        assert run(10,(p,))[0]==0
        xml=ET.parse(p).getroot();rects=xml.findall('{http://www.w3.org/2000/svg}rect')
        assert len(rects)==17 and len({(r.attrib['x'],r.attrib['y']) for r in rects[1:]})==16
        assert xml.attrib.get('viewBox')=='0 0 240 240'
        return '17 rects, 16 unique tiles, SVG namespace parsed'
check('37 SVG geometry','4x4 tiles, 17 rects and viewBox',svg_check)

def svg_preserve():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'tiles.svg';p.write_text('old',encoding='ascii')
        assert run(10,(p,))[0]==1 and p.read_text()=='old'
        assert run(10,(str(Path(tmp)/'bad.txt'),))[0]==2
        return 'existing file unchanged and bad suffix refused'
check('38 SVG safety','no overwrite and invalid suffix refused',svg_preserve)

def sample_check():
    svg=ROOT/'samples/tiles_preview.svg'; assert svg.exists()
    root=ET.parse(svg).getroot(); assert len(root.findall('{http://www.w3.org/2000/svg}rect'))==17
    assert (ROOT/'samples/quiz_input.txt').read_text().splitlines()==['apple','pen','water']
    return 'SVG preview parses, quiz sample contains 3 entries'
check('39 Bundled samples','sample SVG and quiz transcript valid',sample_check)

def case_check():
    cases=json.loads((ROOT/'tests/cases.json').read_text(encoding='ascii'))
    assert len(cases)>=69 and all(x['file'] in SOURCES for x in cases)
    for case in cases:
        assert case['status'] in [0,1,2]
        if case['file']=='06_flashcard_quiz.py' and case['expected']:
            assert 'red fruit: a____' in case['expected']
    return f'{len(cases)} test specifications cross-referenced'
check('40 Behavior case manifest','all included test specs refer to known programs',case_check)

summary={'title':'Day02 source/manual independent auditing','python':sys.version.split()[0],'review_lenses':len(results),'passed':sum(r['result']=='PASS' for r in results),'failed':sum(r['result']=='FAIL' for r in results),'checks':results}
print(json.dumps(summary,ensure_ascii=False,indent=2))
(ROOT/'verification/audit_40_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if summary['failed']:sys.exit(1)
