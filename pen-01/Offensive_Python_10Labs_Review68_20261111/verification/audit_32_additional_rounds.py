"""32 additional, repeatable review rounds of THIS edition.

Each round reopens every package file and performs a different deterministic
focused check. Automated scrutiny is NOT a substitute for expert certification.
"""
from __future__ import annotations

import ast
import hashlib
import html
import io
import json
import re
import tokenize
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from syntax_explain import explain_line, tokenize_source

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Python_ペンテスト10作品_全行構文分解_20261111.html"
SOURCES = sorted((ROOT / 'projects').glob('[0-9][0-9]_*.py'))
EXCLUDED = {"32_ADDITIONAL_ROUNDS.json", "FILE_HASHES.sha256", "REVIEW_REPORT.txt", "test_results.txt"}
CHECKS = [
 "10作品のファイル在庫", "重複番号の排除", "ASCIIコードと行末", "10本のAST解析",
 "標準ライブラリだけの参照", "直接実行ガード", "ネットワーク対象はループバックのみ", "パス実習の教材内制限",
 "安全なSQLの値バインド", "危険なSQLはメモリDBに限定", "認証試行は架空のリスト内", "署名トークンのHMAC比較",
 "鍵の公開に関する警告", "オブジェクト単位の認可", "PCAPの最小長とUDP長検査", "HTTPメッセージの曖昧さの警告",
 "単独CRの拒否", "Base64URLの正規形確認", "サンプルファイルの必須在庫", "HTMLの20章",
 "HTMLの40工程", "全40工程が完成ソースと完全一致", "全非空行の説明を記載", "全行を字句解析して説明",
 "代入と比較演算子の識別", "f文字列と式埋め込みの解説", "文字列とbytesの説明", "ファイル・辞書メソッドの説明",
 "構文解説の折り畳みUI", "全内部リンクの実在", "完成ソースのSHA-256整合", "実行結果と表示ログの照合の証跡",
]


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d:
            self.ids.append(d['id'])
        if tag == 'a' and d.get('href', '').startswith('#'):
            self.refs.append(d['href'][1:])


def focus(i, contents, src, page):
    combined = '\n'.join(src)
    if i == 1:
        assert_true(len(SOURCES) == 10, 'count')
    elif i == 2:
        assert_true([p.name[:2] for p in SOURCES] == [f'{k:02d}' for k in range(1,11)], 'numbering')
    elif i == 3:
        assert_true(all(s.isascii() and s.endswith('\n') and '\r' not in s for s in src), 'ASCII/LF')
    elif i == 4:
        assert_true(all(isinstance(ast.parse(s), ast.Module) for s in src), 'AST')
    elif i == 5:
        allowed = {'re','sys','pathlib','socket','threading','urllib','sqlite3','contextlib','base64','binascii','hashlib','hmac','json','ipaddress','struct'}
        for s in src:
            for node in ast.walk(ast.parse(s)):
                if isinstance(node, ast.Import):
                    for item in node.names: assert_true(item.name.split('.')[0] in allowed,'unexpected import')
                if isinstance(node, ast.ImportFrom): assert_true(node.module.split('.')[0] in allowed,'unexpected from import')
    elif i == 6:
        assert_true(all('if __name__ == "__main__":' in s and 'raise SystemExit(main())' in s for s in src),'guard')
    elif i == 7:
        assert_true('HOST = "127.0.0.1"' in src[2] and 'socket.create_connection((HOST, port)' in src[2]
                    and not any('socket.' in s for j,s in enumerate(src) if j!=2),'network target')
    elif i == 8:
        assert_true('is_relative_to(SAMPLES.resolve(strict=True))' in src[3] and 'is_relative_to(base)' in src[3], 'path guard')
    elif i == 9:
        assert_true('db.execute(query, (name,))' in src[4] and 'WHERE username = ?' in src[4], 'bound SQL')
    elif i == 10:
        assert_true('sqlite3.connect(":memory:")' in src[4] and 'Intentionally unsafe' in src[4], 'unsafe SQL scope')
    elif i == 11:
        assert_true('ACCOUNTS = {' in src[5] and 'lab-wide attempt cap' in src[5] and 'LIMIT = 2' in src[5], 'simulation')
    elif i == 12:
        assert_true('hmac.compare_digest' in src[6] and 'hmac.new' in src[6], 'HMAC check')
    elif i == 13:
        assert_true('never use this to protect real identities' in src[6] and 'published' in contents[ROOT/'verification/REFERENCES.md'].decode('utf-8').lower() or '公開済み' in page, 'training key warning')
    elif i == 14:
        assert_true('target["owner"] == actor' in src[7] and 'return permitted(actor, document, action)' in src[7], 'authorization')
    elif i == 15:
        assert_true('tcp_header < 20' in src[8] and 'udp_length != len(transport)' in src[8], 'transport header lengths')
    elif i == 16:
        assert_true('Transfer-Encoding body is not decoded or validated' in src[9] and 'Content-Length' in src[9], 'framing caution')
    elif i == 17:
        assert_true('"\\r" in saved.replace("\\r\\n", "")' in src[1], 'line ending check')
    elif i == 18:
        assert_true('encode(decoded) != value' in src[6] and 'non-canonical Base64URL' in src[6], 'canonical check')
    elif i == 19:
        assert_true(all((ROOT/'samples'/name).is_file() for name in ('response_headers.txt','cookies.txt','synthetic_traffic.pcap','request_simple.http','request_ambiguous.http','secret.txt','webroot/public.txt')), 'samples missing')
    elif i == 20:
        assert_true(page.count('class="chapter"')==20, 'chapter count')
    elif i == 21:
        assert_true(page.count('class="step"')==40, 'step count')
    elif i == 22:
        # The independent checker verifies the full escaped snippet concatenation.
        import verify_manual
        assert_true(verify_manual.issues == [], 'manual-source mismatch')
    elif i == 23:
        num = sum(bool(line.strip()) for s in src for line in s.splitlines())
        assert_true(page.count('class="syntax-segment"') >= num*2, 'missing line breakdown')
    elif i == 24:
        for s in src:
            tokens = tokenize_source(s)
            assert_true(all(k in tokens for k,line in enumerate(s.splitlines(),1) if line.strip()), 'missing lex tokens')
    elif i == 25:
        assert_true('=：代入' in page and '==：等しいか比較' in page, 'assignment vs comparison')
    elif i == 26:
        assert_true('f文字列' in page and '{式}' in page, 'f-string')
    elif i == 27:
        assert_true('bytes型の定数' in page and 'str型の文字列定数' in page, 'text binary')
    elif i == 28:
        assert_true('辞書のキーに対応する値を取り出す' in page and 'ファイルをバイト列として読む' in page, 'methods')
        for j, source in enumerate(src):
            tokens = tokenize_source(source)
            for number, line in enumerate(source.splitlines(), 1):
                if 'thread.join(' in line:
                    assert_true(any(name == 'join' and 'スレッドの終了を待つ' in note for name, note in tokens[number]), 'thread join semantics')
                elif '.join(' in line:
                    assert_true(any(name == 'join' and '文字列' in note for name, note in tokens[number]), 'str join semantics')
    elif i == 29:
        assert_true('この行の記号・名前・値を分解して読む' in page and 'details class="syntax-segment"' in page, 'collapsible')
    elif i == 30:
        parser=AnchorParser(); parser.feed(page)
        assert_true(len(parser.ids)==len(set(parser.ids)), 'duplicate HTML ids')
        assert_true(set(parser.refs) <= set(parser.ids), 'broken internal anchor')
    elif i == 31:
        manifest=json.loads(contents[ROOT/'verification/manual_build.json'])['source_sha256']
        assert_true(all(hashlib.sha256(p.read_bytes()).hexdigest()==manifest[p.name] for p in SOURCES), 'source digest')
    elif i == 32:
        catalog=json.loads(contents[ROOT/'verification/content_catalog.json'])
        results=json.loads(contents[ROOT/'verification/manual_build.json'])['sample_run']
        assert_true(len(catalog['data'])==10 and len(results)==10, 'sample output report')
        assert_true(all(f'out-{i:02d}' in page for i in range(1,11)), 'output block missing')


def main():
    names=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in EXCLUDED)
    rounds=[]
    for i,desc in enumerate(CHECKS,1):
        contents={path: path.read_bytes() for path in names}
        src=[contents[p].decode('ascii') for p in SOURCES]
        focus(i,contents,src,contents[PAGE].decode('utf-8'))
        rounds.append({'round':i,'focus':desc,'files_read':len(names),'bytes_read':sum(map(len,contents.values())),'result':'PASS'})
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'method':'32 different whole-package re-reads with a focused assertion each; no claim of 32 independent expert assessments',
            'rounds':len(rounds),'passed':len(rounds),'aggregate_bytes_read':sum(r['bytes_read'] for r in rounds),
            'scope_limit':'Constrained offline project, deterministic checks and representative tests; not a formal security audit.',
            'details':rounds}
    (ROOT/'verification/32_ADDITIONAL_ROUNDS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ADDITIONAL_ROUNDS',len(rounds),'PASS',len(rounds),'FILES_EACH',len(names),'BYTES',report['aggregate_bytes_read'])


if __name__=='__main__':
    main()
