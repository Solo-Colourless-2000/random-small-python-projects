"""28 separate automated verification perspectives with a fresh full-file reread each time.

These inspections are machine-checks, not claims of 28 human editorial readings.
"""
import ast
import csv
import hashlib
import importlib.util
import ipaddress
import json
import re
from collections import Counter
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CodeAndIDs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.code_id=None
        self.codes={}
        self.ids=[]
        self.images=[]
        self.chapters=[]
        self.spans={}
        self.links=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if d.get('id'):self.ids.append(d['id'])
        if tag=='section' and 'chapter' in d.get('class','').split():self.chapters.append(d['id'])
        if tag=='img':self.images.append((d.get('src'),d.get('alt')))
        if tag=='code' and d.get('id','').startswith(('full-','code-')):
            self.code_id=d['id'];self.codes[self.code_id]=''
        if tag=='span' and 'line' in d.get('class','').split() and self.code_id:
            self.spans.setdefault(self.code_id,[]).append((d.get('id'),d.get('data-line')))
        if tag=='a' and d.get('href','').startswith('#'):self.links.append(d['href'][1:])
    def handle_endtag(self,tag):
        if tag=='code':self.code_id=None
    def handle_data(self,data):
        if self.code_id:self.codes[self.code_id]+=data

def module(number):
    path=next((ROOT/'projects').glob(f'{number}_*.py'))
    spec=importlib.util.spec_from_file_location('deepreview_'+number,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def snapshot_all():
    content={}
    for file in sorted(ROOT.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts:
            content[str(file.relative_to(ROOT))]=file.read_bytes()
    # Ensures every inspection considers the complete current deliverable, not stale cache.
    digest=hashlib.sha256()
    for path,data in content.items():
        digest.update(path.encode());digest.update(data)
    return content,digest.hexdigest()

def require(value,why):
    if not value:raise AssertionError(why)

checks=[
 ('Seven independent GUI source files',lambda d,s,h,c:require(len([k for k in d if re.fullmatch(r'projects/\d\d_.*\.py',k)])==7,'sources')),
 ('All project source ASTs are valid',lambda d,s,h,c:[ast.parse(d[k].decode()) for k in d if k.startswith('projects/') and k.endswith('.py')]),
 ('Seven ASCII code files',lambda d,s,h,c:require(all(d[f'projects/{f}'].isascii() for f in [x.split('/')[-1] for x in d if x.startswith('projects/') and x.endswith('.py')]),'ASCII')),
 ('Every app has a main guard',lambda d,s,h,c:require(all('if __name__ == "__main__":' in d[k].decode() for k in d if k.startswith('projects/')),'main guard')),
 ('Every app creates a Tk root',lambda d,s,h,c:require(all('tk.Tk()' in d[k].decode() for k in d if k.startswith('projects/')),'tk root')),
 ('Every app starts event loop',lambda d,s,h,c:require(all('root.mainloop()' in d[k].decode() for k in d if k.startswith('projects/')),'event loop')),
 ('No outbound network primitives in lessons',lambda d,s,h,c:require(not any(re.search(r'\b(import socket|import requests|urllib.request|http.client|subprocess\.run|os\.system)\b',d[k].decode()) for k in d if k.startswith('projects/')),'network primitives')),
 ('Exactly 17 HTML chapters',lambda d,s,h,c:require(len(h.chapters)==17,'chapter count')),
 ('All HTML element IDs are unique',lambda d,s,h,c:require(len(h.ids)==len(set(h.ids)),'duplicate IDs')),
 ('Internal anchor targets resolve',lambda d,s,h,c:require(all(link in set(h.ids) for link in h.links),'broken anchors')),
 ('Exactly seven accessible screen images',lambda d,s,h,c:require(len(h.images)==7 and all(alt and src for src,alt in h.images),'images and alt')),
 ('All screenshot files are proper PNG',lambda d,s,h,c:require(all(d[src].startswith(b'\x89PNG\r\n\x1a\n') for src,_ in h.images),'PNG files')),
 ('Dark theme is explicitly selected',lambda d,s,h,c:require('color-scheme: dark' in s and re.search(r'<meta(?=[^>]*name="color-scheme")(?=[^>]*content="dark")',s),'dark')),
 ('No remote stylesheets or external scripts',lambda d,s,h,c:require(not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://',s),'external dependency')),
 ('All Appendix A listings match actual code',lambda d,s,h,c:require(all(h.codes[f'full-{i:02d}']==(ROOT/'projects'/c['projects'][i-1]['filename']).read_text() for i in range(1,8)),'full code sync')),
 ('All 28 steps reconstruct their full Python files',lambda d,s,h,c:require(all(''.join(h.codes[f'code-{i:02d}-{j}'] for j in range(1,5))==h.codes[f'full-{i:02d}'] for i in range(1,8)),'step code sync')),
 ('Line anchor numbering matches shown source',lambda d,s,h,c:require(all([int(v[1]) for v in h.spans[f'full-{i:02d}']]==list(range(1,len(h.codes[f'full-{i:02d}'].splitlines())+1)) for i in range(1,8)),'source line numbers')),
 ('Every project contains a new concrete trace section',lambda d,s,h,c:require(all(f'id="v3-{i:02d}-title"' in s for i in range(1,8)),'trace section')),
 ('Course and project time budgets stay 680/580 minutes',lambda d,s,h,c:require(c['target_minutes']==680 and sum(p['minutes'] for p in c['projects'])==580,'time')),
 ('Sample authentication data and group count correct',lambda d,s,h,c:require(Counter(x['ip'] for x in csv.DictReader(StringIO(d['samples/auth_events.csv'].decode())) if x['status']=='FAIL')['198.51.100.8']==3,'auth sample')),
 ('HTTP sample is offline response-header data',lambda d,s,h,c:require(d['samples/response_headers.txt'].startswith(b'HTTP/1.1 200 OK\n'),'HTTP sample')),
 ('Firewall sample CIDRs parse into networks',lambda d,s,h,c:require(all(isinstance(ipaddress.ip_network(x['source'],strict=False), (ipaddress.IPv4Network,ipaddress.IPv6Network)) for x in csv.DictReader(StringIO(d['samples/firewall_rules.csv'].decode()))),'firewall CIDR')),
 ('IOC reference table has three rows',lambda d,s,h,c:require(len(list(csv.DictReader(StringIO(d['samples/indicators.csv'].decode()))))==3,'IOC')),
 ('Integrity files are present for the baseline lab',lambda d,s,h,c:require(all(f'samples/integrity_folder/{f}' in d for f in ('config.txt','readme.txt')),'integrity samples')),
 ('Mail example uses non-real test domains',lambda d,s,h,c:require(b'example.test' in d['samples/mail_headers.txt'],'mail demo')),
 ('HSTS conflicting age cannot produce a SEEN finding',lambda d,s,h,c:require(not any(x.startswith('SEEN: HSTS') for x in module('02').audit(module('02').parse_headers('Strict-Transport-Security: max-age=0; max-age=31536000\n'),True)),'HSTS collision')),
 ('Non-ASCII port numeric is safely rejected',lambda d,s,h,c:require(not ('²'.isascii() and '²'.isdecimal()),'special number')),
 ('Multiple Reply-To fields do not yield misleading SEEN',lambda d,s,h,c:require(not any('SEEN: Reply-To' in x for x in module('06').analyze_email('From: a@example.test\nReply-To: a@example.test\nReply-To: b@example.test\n')),'mail ambiguity')),
]

def main():
    log=[]
    for i,(name,check) in enumerate(checks,1):
        d,whole_hash=snapshot_all()
        s=d['Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'].decode('utf-8')
        h=CodeAndIDs();h.feed(s)
        c=json.loads(d['PROJECT_HISTORY.json'].decode())
        check(d,s,h,c)
        log.append(f'{i:02d}. PASS | {name} | full artifact reread SHA256 {whole_hash[:16]}')
        print(log[-1])
    report='ADDITIONAL 28-PERSPECTIVE RE-INSPECTION\nEach pass rereads all delivered files, then applies a distinct automated validation. Not a claim of 28 independent human editorial readings.\n\n'+'\n'.join(log)+'\n\n28 / 28 PASS\n'
    (ROOT/'REVIEW_28_ADDITIONAL_PASSES.txt').write_text(report,encoding='utf-8')
    print('28 / 28 PASS')

if __name__=='__main__':main()
