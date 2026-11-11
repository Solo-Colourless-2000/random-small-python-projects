"""30 differentiated review passes; all package files are physically read each pass.

A PASS is a documented automated check, not a claim of an independent manual proof.
"""
from __future__ import annotations
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILES = sorted((BASE / 'projects').glob('[0-9][0-9]_*.py'))
HTML_FILE = BASE / 'Python_ペンテスト10作品_全行構文分解_20261111.html'
SKIP = {'30_CHECK_AUDIT.json', '28_CHECK_AUDIT.json', '26_PASS_AUDIT.json', '24_PASS_AUDIT.json', 'REVIEW_REPORT.txt', 'test_results.txt', 'browser_checks.json'}


def load(number):
    path = FILES[number - 1]
    spec = importlib.util.spec_from_file_location(f'audit_lab_{number}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require(expression, reason):
    if not expression:
        raise AssertionError(reason)


def check_focus(index, data, sources):
    text = data[HTML_FILE].decode('utf-8')
    if index == 1:
        require(len(FILES) == 10, 'ten labs required')
    elif index == 2:
        require([p.name[:2] for p in FILES] == [f'{n:02d}' for n in range(1, 11)], 'numbered source inventory')
    elif index == 3:
        require(all(s.isascii() and s.endswith('\n') for s in sources), 'ASCII and final LF')
    elif index == 4:
        for p,s in zip(FILES,sources): ast.parse(s, filename=p.name)
    elif index == 5:
        require(all('if __name__ == "__main__"' in s for s in sources), 'direct-execution guard')
    elif index == 6:
        hashes=json.loads(data[BASE/'verification/manual_build.json'].decode())['source_sha256']
        require(all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p.name] for p in FILES), 'project hashes')
    elif index == 7:
        require('REVIEW CSP' in sources[0] and 'name != "set-cookie"' in sources[0], 'response header scope')
    elif index == 8:
        mod=load(1)
        require(not any('duplicate: set-cookie' in m for m in mod.inspect({'set-cookie':['x=a','y=b']}, 'https')), 'Set-Cookie repetition')
    elif index == 9:
        mod=load(2)
        _,_,attrs=mod.parse_cookie('Set-Cookie: x=v; Secure=0; HttpOnly=no; SameSite=None')
        result=' '.join(mod.review('x',attrs))
        require('unexpected secure flag value' in result and 'requires Secure' not in result, 'RFC 6265 Secure semantics')
    elif index == 10:
        mod=load(3)
        require(mod.HOST=='127.0.0.1', 'TCP confined to loopback')
    elif index == 11:
        mod=load(4)
        require('secret.txt' in str(mod.choose(mod.ROOT,'../secret.txt','unsafe')), 'toy unsafe path must demonstrate')
        try: mod.choose(mod.ROOT,'../secret.txt','safe')
        except ValueError: pass
        else: raise AssertionError('safe traversal accepted')
    elif index == 12:
        mod=load(5)
        require(mod.find_accounts('unsafe',"' OR 1=1 --")==['alice','bob'], 'unsafe SQL demonstration')
        require(mod.find_accounts('safe',"' OR 1=1 --")==[], 'safe binding')
    elif index == 13:
        mod=load(6)
        with contextlib.redirect_stdout(io.StringIO()):
            unprotected=mod.simulate('unprotected')
            protected=mod.simulate('protected')
        require(unprotected==(4,['alice','carol']) and protected==(2,['alice']), 'lab-wide cap not a rate limiter')
    elif index == 14:
        mod=load(7)
        token=mod.create('alice','viewer')
        require(mod.verify(token)['role']=='viewer','genuine token')
        forged=mod.tamper(token,'admin')
        try: mod.verify(forged)
        except ValueError: pass
        else: raise AssertionError('MAC tampering accepted')
    elif index == 15:
        mod=load(8)
        require(mod.check_access('unsafe','alice','notes','read') is True,'IDOR unsafe')
        require(mod.check_access('safe','alice','notes','read') is False,'IDOR safe')
    elif index == 16:
        mod=load(9)
        result=mod.parse_pcap(BASE/'samples/synthetic_traffic.pcap')
        require(len(result)==2 and any('TCP ' in r for r in result) and any('UDP ' in r for r in result),'PCAP fixture')
        require('udp_length' in sources[8] and 'tcp_header' in sources[8] and 'snaplen' in sources[8], 'transport lengths')
    elif index == 17:
        mod=load(10)
        require(any('Transfer-Encoding with Content-Length' in r for r in mod.check_request((BASE/'samples/request_ambiguous.http').read_bytes())), 'TE+CL')
        try: mod.check_request(b'GET / HTTP/1.1\r\nHost: x\nZ: 1\r\n\r\n')
        except ValueError: pass
        else: raise AssertionError('bare LF accepted')
    elif index == 18:
        require(all((BASE/'samples'/f).exists() for f in ('response_headers.txt','cookies.txt','synthetic_traffic.pcap','request_ambiguous.http','request_simple.http','secret.txt','webroot/public.txt')), 'sample inventory')
    elif index == 19:
        require(text.count('class="chapter"')==20 and text.count('class="step"')==40, '20 chapters and 40 steps')
    elif index == 20:
        from html.parser import HTMLParser
        class IDs(HTMLParser):
            def __init__(self):super().__init__();self.ids=[];self.href=[]
            def handle_starttag(self,tag,attrs):
                d=dict(attrs)
                if 'id' in d:self.ids.append(d['id'])
                if d.get('href','').startswith('#'):self.href.append(d['href'][1:])
        parser=IDs();parser.feed(text)
        require(len(parser.ids)==len(set(parser.ids)),'duplicate ids')
        require(all(ref in parser.ids for ref in parser.href),'broken local references')
    elif index == 21:
        from verify_manual import parser, issues
        require(not issues and parser.steps==40,'HTML source/step integrity')
    elif index == 22:
        from build_manual import note_for
        for n,s in enumerate(sources,1):
            for line in s.splitlines():
                if line.strip():
                    note=note_for(n,line)
                    require(len(note)>15 and '直前の条件や関数の文脈' not in note, f'weak line note: {n} {line}')
    elif index == 23:
        from build_manual import DATA
        require(sum(d['mins'] for d in DATA)==600,'600-minute basic lab route')
        require('720分' in text and text.count('発展解説：実装とセキュリティ仕様')==10,'time and optional notes')
    elif index == 24:
        readme=data[BASE/'README.md'].decode('utf-8')
        require(HTML_FILE.name in readme and 'audit_30_checks.py' in readme, 'README paths')
        require('RFC 6265' in text and 'RFC 9112' in text, 'standards references')
        require('22pass_refined.zip' not in readme, 'stale ZIP guidance')
    elif index == 25:
        mod=load(3)
        from unittest.mock import patch
        with patch.object(mod,'probe', return_value=('CLOSED/UNREACHABLE','')):
            with patch.object(mod.sys,'argv',['probe.py','check','12345']):
                require(mod.main()==1,'closed TCP must return failure')
        with patch.object(mod,'probe', return_value=('OPEN','')):
            with patch.object(mod.sys,'argv',['probe.py','check','12345']):
                require(mod.main()==0,'open TCP without banner must return success')
        require('LIMIT = 2' in sources[5],'cap must be pedagogically visible')
    elif index == 26:
        mod=load(9)
        frame=bytearray(14+20+10); frame[12:14]=b'\x08\x00';frame[14]=0x45;frame[16:18]=(30).to_bytes(2,'big');frame[23]=17
        frame[14+20+4:14+20+6]=(8).to_bytes(2,'big')
        require('invalid UDP length' in mod.summarize_frame(frame),'UDP shorter than IPv4 payload accepted')
        mod=load(10)
        msg=b'POST / HTTP/1.1\r\nHost: demo\r\nContent-Length: '+b'9'*5000+b'\r\n\r\n'
        require('oversized Content-Length' in str(mod.check_request(msg)), 'huge CL must be a review, not conversion error')
        try: mod.check_request(b'GET /bad\x00 HTTP/1.1\r\nHost: demo\r\n\r\n')
        except ValueError: pass
        else: raise AssertionError('invalid target control accepted')
    elif index == 27:
        mod=load(1)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'headers.txt'
            f.write_bytes(b'HTTP/1.1 200 OK\r\nContent-Security-Policy:\r\n\r\nX-Test: in-body\r\n')
            fields=mod.read_headers(f)
            require(fields['content-security-policy']==[''] and 'x-test' not in fields,'headers / body boundary')
            require('missing or empty' in ' '.join(mod.inspect(fields,'https')), 'empty policy must trigger review')
            f.write_bytes(b'X-Test: a\rhidden')
            try: mod.read_headers(f)
            except ValueError:pass
            else:raise AssertionError('bare CR accepted')
    elif index == 28:
        mod=load(2)
        try:mod.parse_cookie('Set-Cookie: id="abc; Secure')
        except ValueError:pass
        else:raise AssertionError('unbalanced quote accepted')
        from unittest.mock import patch
        probe=load(3)
        class Broken:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def settimeout(self,*args):return None
            def recv(self,*args):raise ConnectionResetError('read failed')
        with patch.object(probe.socket,'create_connection',return_value=Broken()):
            require(probe.probe(12345)==('OPEN','(banner read failed)'), 'TCP success mistaken for read failure')
        token_mod=load(7)
        import json as js
        payload=token_mod.encode(js.dumps({'role':'admin','user':'alice'},sort_keys=True,separators=(',',':')).encode())
        require(token_mod.verify(payload+'.'+token_mod.encode(token_mod.sign(payload)))['role']=='admin', 'published key caveat')
    elif index == 29:
        # Every conditional that formerly had boilerplate must now explain the specific condition.
        from build_manual import SPECIFIC_CONDITIONS, note_for
        require(len(SPECIFIC_CONDITIONS)>=35,'conditional explanations coverage')
        require(all(len(note)>24 for note in SPECIFIC_CONDITIONS.values()), 'specific condition explanation too short')
        for n,source in enumerate(sources,1):
            for line in source.splitlines():
                if line.strip().startswith(('if ','elif ')):
                    require('条件を評価し、真であれば' not in note_for(n,line),f'generic conditional explanation: {n}: {line}')
        require('全行構文分解_20261111' in HTML_FILE.name, 'manual new name')
        require('追加28観点再監査_全行詳説.html' not in data[BASE/'README.md'].decode(), 'stale manual in README')
    elif index == 30:
        # The actual Chromium viewport checks must be complete and all passing.
        for group,expected in (('small',72),('large',69)):
            payload=json.loads(data[BASE/'verification'/f'layout_{group}.json'].decode('utf8'))
            require(payload['total']>=expected and payload['passed']==payload['total'] and not payload['failed'], f'{group} viewport overflow')
        require(all((BASE/'verification'/x).is_file() for x in ('mobile_layout.png','desktop_layout.png','mobile_code_layout.png')), 'missing layout screenshots')
        require('max-width: 430px' in data[BASE/'verification/style_base.css'].decode('utf8'), 'mobile layout CSS absent')
    return True


FOCUS=[
    '10本のファイル存在','番号順と独立性','ASCIIと最終改行','Python AST構文',
    '直接実行ガード','SHA-256整合','レスポンスヘッダー方針','Set-Cookie複数行',
    'CookieのSecure値と属性の違い','ループバック固定','トラバーサル境界',
    'SQL構造と値の分離','スプレー試行の制限','トークンHMACの改ざん拒否',
    'IDOR認可の差','PCAPとTCP/UDP長','HTTP要求の競合と不正改行',
    'サンプルファイル在庫','HTML20章40工程','HTML内部リンク',
    'コード工程と付録の一致','逐行説明の存在・品質','600分の計画と発展解説',
    'READMEの参照とRFC根拠',
    'TCP失敗の終了状態と総試行上限','UDP長一致・HTTP過大入力・target制御文字',
    'HTTP空値と本文境界・単独CRの拒否',
    'Cookie引用符・TCP受信例外・教材公開鍵の限界',
    '条件分岐の個別逐行解説と旧ファイル名の排除',
    '320〜1920pxブラウザ141件のレイアウト検査と画像',
]


def main():
    files=sorted(p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in SKIP)
    record=[]
    bytes_total=0
    for i,focus in enumerate(FOCUS,1):
        data={p:p.read_bytes() for p in files}
        sources=[data[p].decode('ascii') for p in FILES]
        require(HTML_FILE in data,'manual missing')
        check_focus(i,data,sources)
        amount=sum(len(b) for b in data.values())
        bytes_total+=amount
        record.append({'pass':i,'focus':focus,'files_scanned':len(files),'bytes_scanned':amount,'result':'PASS'})
    report={'passes':len(record),'files_per_pass':len(files),'total_bytes_read':bytes_total,'records':record,
            'limits':'30 differentiated automated checks and file rereads; not independent human peer review or exhaustive proof.'}
    (BASE/'verification/30_CHECK_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'AUDIT_PASSES={len(record)} FILES_PER_PASS={len(files)} TOTAL_BYTES_READ={bytes_total} ERRORS=0')

if __name__=='__main__':main()
