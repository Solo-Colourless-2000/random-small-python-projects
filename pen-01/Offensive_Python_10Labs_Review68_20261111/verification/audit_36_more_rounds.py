"""36 NEW full-package deterministic review focuses for this revision.

A round reopens the inspectable content files, excluding cyclic review reports and the checksum manifest, then performs one focused check.
This is NOT 36 independent manual security audits. Full behavior coverage is
provided separately through focused unit, example, DOM, and viewport tests.
"""
from __future__ import annotations
import ast, hashlib, io, json, os, re, subprocess, sys, tokenize
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SOURCES=sorted((ROOT/'projects').glob('[0-9][0-9]_*.py'))
HTML=ROOT/'Python_ペンテスト10作品_全行構文分解_20261111.html'
EXCLUDES={'36_MORE_ROUNDS.json','FILE_HASHES.sha256','REVIEW_REPORT.txt'}
CHECKS=[
'01 10件の完成ソースが存在','02 番号とファイル名に重複がない','03 すべてAST解析可能',
'04 すべてコンパイル可能','05 コードはASCII・LF・末尾改行','06 importは指定した標準ライブラリのみ',
'07 直接実行ガードが存在','08 すべての作品にUsage表示がある','09 外部HTTPライブラリによる通信がない',
'10 TCP接続先が127.0.0.1固定','11 TCP接続とバナー取得がタイムアウト付き','12 ファイル読み込みはサイズの上限付き',
'13 HTTPレスポンス名は構文検査','14 保存Cookieの単独CRを拒否','15 Cookie名と属性名は厳格に検査',
'16 Cookie __Host・__Secure の警告が存在','17 4つの関数で不明な動作モードを拒否',
'18 unsafeパスもsamples外を拒否','19 URL復号の厳格さとNUL拒否',
'20 危険なSQLはmemory DBだけ','21 安全なSQLはバインド引数',
'22 スプレー入力は合成アカウントのみ','23 試行制限は条件判定で実装',
'24 署名はHMAC-SHA256','25 MAC比較にcompare_digest','26 Base64URLは正規形を検査',
'27 署名付きpayloadは型・長さを検査','28 閲覧の認可は文書所有者を検査',
'29 PCAPはファイル・レコード長を検査','30 TCP/UDP最低ヘッダー長を検査',
'31 HTTP CL/TEの競合をREVIEW','32 合成サンプルがすべて存在',
'33 HTML 20章と40工程','34 HTML全ソースと完成コードの一致',
'35 重点30行・120構成要素の説明が実ソースに対応','36 HTMLのJavaScriptに構文エラーなし',
]

def yes(value,msg):
 if not value:raise AssertionError(msg)

class Manual(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.depth=0;self.ids=[];self.code='';self.current=None;self.codes={};self.chapters=0;self.steps=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.depth+=1
  if 'id' in a:self.ids.append(a['id'])
  if tag=='section' and 'chapter' in a.get('class','').split():self.chapters+=1
  if tag=='article' and 'step' in a.get('class','').split():self.steps+=1
  if tag=='code' and 'id' in a:self.current=a['id'];self.codes[self.current]=''
 def handle_endtag(self,tag):
  if tag=='code':self.current=None
 def handle_data(self,s):
  if self.current is not None:self.codes[self.current]+=s

def focus(n,files,sources,page):
 s=sources; joined='\n'.join(s)
 if n==1:yes(len(SOURCES)==10,'inventory')
 elif n==2:yes([p.name[:2] for p in SOURCES]==[f'{k:02d}' for k in range(1,11)] and len({p.name for p in SOURCES})==10,'numbering')
 elif n==3:yes(all(isinstance(ast.parse(x),ast.Module) for x in s),'ast')
 elif n==4:yes(all(compile(x,p.name,'exec') for x,p in zip(s,SOURCES)),'compile')
 elif n==5:yes(all(x.isascii() and x.endswith('\n') and '\r' not in x for x in s),'ASCII/LF')
 elif n==6:
  allowed={'re','sys','pathlib','socket','threading','urllib','sqlite3','contextlib','base64','binascii','hashlib','hmac','json','ipaddress','struct'}
  for x in s:
   for v in ast.walk(ast.parse(x)):
    if isinstance(v,ast.Import):yes(all(a.name.split('.')[0] in allowed for a in v.names),'import')
    if isinstance(v,ast.ImportFrom):yes(v.module and v.module.split('.')[0] in allowed,'import-from')
 elif n==7:yes(all('if __name__ == "__main__":' in x and 'raise SystemExit(main())' in x for x in s),'main guard')
 elif n==8:yes(all('Usage: python3' in x for x in s),'usage')
 elif n==9:yes(not any('requests.' in x or 'urllib.request' in x or 'http.client' in x for x in s),'unexpected HTTP')
 elif n==10:yes('HOST = "127.0.0.1"' in s[2] and 'socket.create_connection((HOST, port)' in s[2] and all('socket.' not in x for j,x in enumerate(s) if j!=2),'network boundary')
 elif n==11:yes('timeout=0.5' in s[2] and 'client.settimeout(0.5)' in s[2],'timeouts')
 elif n==12:yes(all('st_size >' in s[i] for i in [0,1,3,8,9]),'size guards')
 elif n==13:yes('re.fullmatch' in s[0] and 'invalid header name' in s[0],'HTTP header')
 elif n==14:yes('saved.replace(' in s[1] and 'bare CR' in s[1],'cookie CR')
 elif n==15:yes('not re.fullmatch(COOKIE_NAME, name)' in s[1] and 'not re.fullmatch(COOKIE_NAME, key)' in s[1],'cookie tokens')
 elif n==16:yes('__Host-' in s[1] and '__Secure-' in s[1] and 'secure_present' in s[1],'prefixes')
 elif n==17:yes(all('if mode not in (' in s[i] for i in [3,4,5,7]),'unknown direct mode')
 elif n==18:yes('if not target.is_relative_to(SAMPLES.resolve(strict=True)):' in s[3],'sandbox')
 elif n==19:yes('unquote(user_path, errors="strict")' in s[3] and 'invalid relative path' in s[3],'decode')
 elif n==20:yes('sqlite3.connect(":memory:")' in s[4],'sqlite')
 elif n==21:yes('db.execute(query, (name,))' in s[4] and 'WHERE username = ?' in s[4],'bind')
 elif n==22:yes('ACCOUNTS = {' in s[5] and 'No network' in s[5] and 'BlueFish7' in s[5],'fake')
 elif n==23:yes('attempts >= LIMIT' in s[5] and 'continue' in s[5],'limit')
 elif n==24:yes('hmac.new(LAB_KEY, message.encode("ascii"), hashlib.sha256)' in s[6],'sha256')
 elif n==25:yes('hmac.compare_digest(sign(payload_part), decode(signature_part))' in s[6],'constant compare')
 elif n==26:yes('if encode(decoded) != value:' in s[6],'base64url canonical')
 elif n==27:yes(all(y in s[6] for y in ('isinstance(user, str)','isinstance(role, str)','len(user) > 32','len(role) > 32')),'type lengths')
 elif n==28:yes('target["owner"] == actor' in s[7] and 'return permitted(actor, document, action)' in s[7],'owner auth')
 elif n==29:yes('pcap exceeds 200000 bytes' in s[8] and 'invalid captured length' in s[8],'PCAP bounds')
 elif n==30:yes('tcp_header < 20' in s[8] and 'udp_length != len(transport)' in s[8],'transport')
 elif n==31:yes('REVIEW Transfer-Encoding with Content-Length' in s[9] and 'REVIEW duplicate Content-Length fields' in s[9],'CL TE')
 elif n==32:
  names=('response_headers.txt','cookies.txt','synthetic_traffic.pcap','request_simple.http','request_ambiguous.http','secret.txt','webroot/public.txt')
  yes(all((ROOT/'samples'/name) in files for name in names),'samples')
 elif n==33:
  m=Manual();m.feed(page);yes(m.chapters==20 and m.steps==40,'chapter/step counts')
 elif n==34:
  m=Manual();m.feed(page)
  for i,code in enumerate(s,1):
   yes(m.codes.get(f'src{i:02d}')==code,'appendix source '+str(i))
   yes(''.join(m.codes.get(f'p{i:02d}-chunk{k}','') for k in range(1,5))==code,'step source '+str(i))
 elif n==35:
  data=json.loads(files[ROOT/'verification/critical_line_walkthroughs.json'])
  yes(len(data)==10,'10 walkthrough lists')
  items=[(int(n),x) for n,lst in data.items() for x in lst]
  yes(len(items)==30 and sum(len(x['pieces']) for _,x in items)==120,'30x4')
  for i,entry in items:
   yes(sum(entry['anchor'] in line for line in s[i-1].splitlines())==1,'unique source anchor')
  yes('重点30行の構文分解' in page,'visible section')
 elif n==36:
  js=page.split('<script>',1)[1].split('</script>',1)[0]
  result=subprocess.run(['node','--check','-'],input=js,text=True,capture_output=True,timeout=8)
  yes(result.returncode==0,'JS syntax: '+result.stderr[:120])
 else:raise AssertionError('unhandled')

def main():
 excluded=EXCLUDES|{'__pycache__'}
 paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in excluded) and p.name not in excluded)
 outcomes=[]
 for n,name in enumerate(CHECKS,1):
  contents={p:p.read_bytes() for p in paths}
  src=[contents[p].decode('ascii') for p in SOURCES]
  focus(n,contents,src,contents[HTML].decode('utf8'))
  outcomes.append({'round':n,'focus':name,'files_read':len(contents),'bytes_read':sum(map(len,contents.values())),'status':'PASS'})
 doc={'created_utc':datetime.now(timezone.utc).isoformat(),
 'definition':'36 distinct focused deterministic checks; every round reopens all inspectable package content files; cyclic reports and checksum list are excluded',
 'scope_warning':'NOT 36 human reviews, not proof of defect-free source or authorization to scan networks',
 'total':len(CHECKS),'passed':len(outcomes),'results':outcomes}
 path=ROOT/'verification/36_MORE_ROUNDS.json';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'36_MORE_ROUNDS {len(outcomes)}/{len(CHECKS)} PASS; {len(paths)} files reopened each round')

if __name__=='__main__':main()
