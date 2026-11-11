"""Build the standalone dark Japanese learning manual from actual source files."""
from __future__ import annotations
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted((ROOT / 'projects').glob('[0-9][0-9]_*.py'))
assert len(FILES) == 10

# Final editorial catalog, free of superseded project definitions.
CATALOG = json.loads((ROOT / "verification" / "content_catalog.json").read_text(encoding="utf-8"))
DATA = CATALOG["data"]
NOTES = {int(number): notes for number, notes in CATALOG["notes"].items()}
REFS = CATALOG["references"]
WALKTHROUGHS = json.loads((ROOT / "verification" / "critical_line_walkthroughs.json").read_text(encoding="utf-8"))
from beginner_notes import BEGINNER, DEEPER
from syntax_explain import explain_line, tokenize_source

LEX = {index: tokenize_source(path.read_text(encoding="ascii")) for index, path in enumerate(FILES, 1)}


def esc(value):
    return html.escape(str(value), quote=True)


def inline(value):
    return f'<code>{esc(value)}</code>'


def p(value, klass=''):
    return f'<p{(" class=" + chr(34) + klass + chr(34)) if klass else ""}>{value}</p>'


def block(text, label='python', ident='', numbering=False, start=1):
    lines = text.splitlines(keepends=True)
    code = []
    for num, line in enumerate(lines, start):
        if numbering:
            code.append(f'<span class="line" data-line="{num}" id="{ident}-L{num}">{esc(line)}</span>')
        else:
            code.append(esc(line))
    pre_class = "numbered" if numbering else ""
    return ('<div class="codebox"><div class="codebar"><span>' + esc(label) +
            '</span><button class="copy js-only" type="button">コピー</button><span class="copy-status" role="status"></span></div>' +
            f'<pre class="{pre_class}" tabindex="0"><code id="{ident}" data-kind="{esc(label)}">' + ''.join(code) + '</code></pre>' +
            '<div class="copy-fallback" hidden><label>手動コピー用<textarea readonly spellcheck="false"></textarea></label></div></div>')


SPECIFIC_CONDITIONS = {(1, 'if len(sys.argv) != 3 or sys.argv[2] not in ("http", "https"):'): 'スクリプト名を含めて引数が3つあるか、通信方式がhttpまたはhttpsかを同時に確認します。片方でも違えばUsageの分岐へ進みます。', (2, 'if not line.lower().startswith(prefix):'): '先頭がSet-Cookie:で始まるかを大文字小文字を無視して検査します。別のヘッダー行なら解析を続けず拒否します。', (2, 'if "=" not in parts[0]:'): '最初の区間に名前と値を区切る等号がなければ、Cookieの基本形式を満たさないので拒否します。', (2, 'if not part:'): 'セミコロンで分割した属性が空の場合は飛ばします。末尾の余分なセミコロンはここで無視します。', (2, 'if flag not in attrs:'): 'Secure/HttpOnlyという属性名が辞書にない場合は、属性不足としてwarningsへ記録します。', (2, 'elif attrs[flag] != "":'): 'SecureやHttpOnlyが存在しても「=0」などの値を伴うと、フラグ属性として紛らわしいため注意します。存在自体は否定しません。', (2, 'if same_site not in ("strict", "lax", "none"):'): 'SameSiteの値を小文字に揃えたうえで、Strict・Lax・Noneのいずれでもなければ注意します。', (2, 'if name.startswith("__Secure-") and not secure_present:'): '名前に__Secure-が付くCookieでSecure属性が見つからなければ、接頭辞に対応する条件が欠けています。', (2, 'if not secure_present or attrs.get("path") != "/" or "domain" in attrs:'): '__Host-接頭辞ではSecure、Path=/、Domain属性なしの3条件を要求します。どれか1つでも違えば警告します。', (2, 'if len(sys.argv) != 2:'): 'ファイル名のほかに入力ファイルをちょうど1つ渡す使い方かを確認します。不足・過剰を防ぎます。', (2, 'if path.stat().st_size > 100_000:'): 'ファイルを読む前にサイズを調べ、10万バイトを超えたら学習用途として扱わず終了します。', (2, 'if not lines:'): '空白行を除いたSet-Cookie行が1つもなければ、何も点検できないので入力エラーとします。', (3, 'if sys.argv[1:] == ["demo"]:'): 'ユーザー引数がdemoだけなら、ローカルで待受と接続確認を行う実験モードへ進みます。', (3, 'if len(sys.argv) != 3 or sys.argv[1] != "check":'): 'checkの後にポート番号を1つだけ渡したか確かめます。引数の形が違えばポート変換を実行しません。', (3, 'if not sys.argv[2].isascii() or not sys.argv[2].isdecimal():'): 'ポート番号にASCII以外の文字や数字以外が含まれていれば拒否します。見かけが数字でも全角数字は不可です。', (4, 'if len(sys.argv) != 3 or sys.argv[1] not in ("unsafe", "safe"):'): 'unsafe/safeの選択と相対ファイル名が正しい順序で渡されたかを確かめます。', (5, 'if mode == "safe":'): 'safeの場合はSQL文と入力値を別々に渡すパラメーター方式を選びます。unsafeの文字列連結とは区別します。', (5, 'if len(sys.argv) != 3 or sys.argv[1] not in ("safe", "unsafe"):'): 'モードとユーザー名をそれぞれ1つ渡したかを確認し、想定外モードでSQLを実行させません。', (5, 'if len(sys.argv[2]) > 80:'): 'ユーザー名の文字数が80を超えたら、データベース処理前に入力を拒否します。', (6, 'if match:'): '試した文字列がその架空アカウントのパスワードと一致した場合だけ、成功一覧へユーザー名を追加します。', (6, 'if len(sys.argv) != 2 or sys.argv[1] not in ("unprotected", "protected"):'): '比較する実習モードを1つだけ指定したかを確かめ、未定義のモードを拒否します。', (7, 'if len(token) > 512 or token.count(".") != 1:'): 'トークンの総文字数を512以下、区切りの点をちょうど1個に制限します。巨大入力や形の違う入力は拒否します。', (7, 'if token.count(".") != 1 or len(token) > 512:'): 'tamper側でも同じ区切り個数と長さを確かめ、想定外の構造を後段へ渡しません。', (7, 'if not isinstance(payload, dict) or set(payload) != {"role", "user"}:'): 'JSONを辞書として読めたことと、キーがuser・roleの2つだけであることを確認します。余分なキーも拒否します。', (7, 'if len(args) == 3 and args[0] == "create":'): 'createモードと2つの入力（user、role）が指定された場合に、新しい署名付き教材トークンを作ります。', (7, 'if not user or len(user) > 32 or not user.isascii() or not user.isalnum() or role not in ("viewer", "editor"):'): '利用者名の空文字・32文字超・非ASCII・英数字以外と、未知のroleを一括で拒否します。条件はorで結ばれ、1つでも違えばエラーです。', (8, 'if len(sys.argv) != 5 or sys.argv[1] not in ("unsafe", "safe"):'): 'mode、actor、document、actionを4引数で受け取ったかと、modeが既知かを確認します。', (8, 'if action not in ("read", "edit"):'): '操作をreadまたはeditに制限します。文字列の違う操作を勝手に許可しません。', (9, 'if protocol not in (6, 17) or packet_length < header_length + 4:'): 'IPv4の上位プロトコルがTCP(6)/UDP(17)か、ポート番号2個を読める最低4バイトがあるかを先に確認します。', (9, 'if protocol == 6:'): 'プロトコル番号6ならTCPヘッダー長を、17ならUDP長フィールドを確認する分岐です。', (9, 'if path.stat().st_size > 200_000:'): '大きなパケットファイルを一括読みしないため、20万バイトを超えるサンプルを拒否します。', (9, 'if len(data) < 24:'): 'classic PCAPのグローバルヘッダーは24バイトです。足りなければファイル形式を判断できません。', (9, 'if (major, minor) != (2, 4) or network != 1 or snaplen < 14 or snaplen > 65535:'): 'PCAP 2.4、Ethernetリンク型1、14〜65535バイトのsnaplenという教材の対応範囲に絞ります。', (9, 'if len(data) - offset < 16:'): '次のパケットレコードヘッダー16バイトが残っているかを確認します。途中で切れた入力を読みません。', (9, 'if len(sys.argv) != 2:'): 'ファイル名を1つだけ受け取る使い方かを確認します。', (10, 'if len(transfers) > 1:'): 'Transfer-Encodingが複数行に分かれている場合、受信者による解釈差につながり得るためREVIEWにします。', (10, 'if value.lower() != b"chunked":'): 'Transfer-Encodingの値を小文字で比較し、教材が想定する単一のchunked以外なら注意を出します。', (10, 'if len(sys.argv) != 2:'): '静的検査するHTTP要求ファイルを1つ渡したかを確認します。', (10, 'if path.stat().st_size > 100_000:'): '読み取るHTTP要求のサンプルを10万バイト以内に制限します。'}


# This revision added explicit direct-call mode guards and signed-field checks.
SPECIFIC_CONDITIONS.update({
    (4, 'if mode not in ("safe", "unsafe"):'): 'chooseを関数として直接呼ばれた場合もモード名がsafeまたはunsafe以外なら拒否します。以前の実装では未知の値をunsafeとして扱う抜け道がありました。',
    (5, 'if mode not in ("safe", "unsafe"):'): 'SQLの関数find_accountsを直接呼ばれても、safeかunsafe以外は例外にします。スペルミスで危険な連結方式へ落ちないようにする入口検査です。',
    (6, 'if mode not in ("protected", "unprotected"):'): 'simulateを直接呼ぶときも、protected/unprotected以外を拒否します。未定義文字列が無制限の試行に変わるのを防ぎます。',
    (8, 'if mode not in ("safe", "unsafe"):'): 'check_accessへsafe/unsafe以外の文字列を渡した場合は拒否します。未定義モードを黙って安全モードと解釈せず、使用側の誤りを検出します。',
    (7, 'if not isinstance(user, str) or not user or len(user) > 32 or not user.isascii() or not user.isalnum():'): '署名検査後でもuserがstrか、空でないか、長すぎないか、ASCII英数字だけかを順に検査します。数字やNoneのuserを受け入れません。',
    (7, 'if not isinstance(role, str) or not role.isascii() or len(role) > 32:'): '署名検査後でもroleの型・文字種・長さを確認します。ただしadminというroleを認可する意味ではなく、権限の妥当性は別途必要です。',
})

def note_for(n, line):
    s = line.strip()
    if (n, s) in SPECIFIC_CONDITIONS:
        return SPECIFIC_CONDITIONS[(n, s)]
    for needle, note in NOTES[n]:
        if needle in s:
            return note
    if s.startswith('"""'):
        return '先頭の三重引用符はモジュールの目的を示すdocstring。これ自体は呼び出し処理を開始しない。'
    if s.startswith('import ') or s.startswith('from '):
        module = s.split()[1].split('.')[0]
        modules = {
            'sys':'コマンドライン引数のsys.argvを読むための標準モジュール。',
            're':'HTTPの許可文字を正規表現で検査する標準モジュール。',
            'pathlib':'Pathでファイルやフォルダーの場所を表す標準モジュール。',
            'socket':'TCPのソケット接続と待ち受けを行う標準モジュール。',
            'threading':'接続待受と接続試行を並行して進めるための標準モジュール。',
            'urllib':'パーセントエンコードを戻すunquoteを提供する標準モジュール。',
            'sqlite3':'外部サーバー不要のSQLiteデータベースを扱う標準モジュール。',
            'contextlib':'withを抜ける際にDB接続をcloseできるclosingを提供する。',
            'base64':'データをBase64URLの文字列として表したり戻したりするモジュール。',
            'binascii':'Base64の不正な入力に関連する例外型を提供する。',
            'hashlib':'HMACで使うSHA-256ハッシュ関数を提供する。',
            'hmac':'共有鍵に基づくメッセージ認証コードの作成と比較に使う。',
            'json':'辞書とJSON文字列の相互変換に使うモジュール。',
            'ipaddress':'4バイトのIPv4アドレスをドット区切り表記へ変換する。',
            'struct':'パケット内の複数バイト整数をバイト順に従って読み取る。',
        }
        return modules.get(module, '使う機能を標準ライブラリから読み込む。')
    if s.startswith('def '):
        return '関数を定義する。これ以降の字下げした行が関数本体になり、呼ばれるまで処理されない。'
    if s.startswith('if __name__'):
        return 'ファイルを直接実行した場合だけmainを起動する入口。モジュールとして読み込んでも自動実行しない。'
    if s.startswith('raise SystemExit'):
        return 'mainの戻り値をOSへ終了ステータスとして返す。成功は0、失敗は1、使い方の誤りは2。'
    if s.startswith('except '):
        return 'try内で想定した例外が起きた場合にだけこの分岐へ進む。検査失敗を握りつぶさず報告する。'
    if s.startswith('try:'):
        return '失敗する可能性のある操作をまとめて開始。対応するexceptと字下げの範囲を意識する。'
    if s.startswith('raise '):
        return f'不正な入力を検出して{s}を実行する。原因を表す例外を外側のexceptへ伝え、これ以降の処理を実行させない。'
    if s == 'return 0':
        return '処理を正常終了し、mainから終了コード0を返す。printの内容とOSの終了コードは別。'
    if s == 'return 1':
        return 'ここで処理を中止し、入力ファイルや検査の失敗を終了コード1で知らせる。'
    if s == 'return 2':
        return 'コマンド引数の個数・形式などが違うため、使い方の誤りを終了コード2で知らせる。'
    if s == 'return True':
        return '許可条件を満たしたので真偽値Trueを返す。どの条件を通ったか直前のifと合わせて読む。'
    if s == 'return False':
        return '許可条件を満たさないため偽のFalseを返す。未知の入力を許可しない。'
    if s.startswith('return '):
        return f'関数から {s[7:]} の評価結果を返す。表示するだけでなく呼び出し元に結果を渡す操作。' 
    if s.startswith('print('):
        return '計算・検査した結果を標準出力へ表示する。文字列への変換やf文字列の埋め込みもここで行う。'
    if s.startswith('notes.append('):
        return '検査結果の文章をnotesリストへ追加する。ここで追加した順序で最後に結果を表示する。'
    if s.startswith('warnings.append('):
        return 'Cookieに関する注意事項をwarningsの末尾へ追加する。ルールに該当した場合だけリストが増える。'
    if s.startswith('alerts.append('):
        return '条件を満たした検出結果を一覧に追加する。'
    if s.startswith('}'): 
        return '波括弧で辞書の定義を閉じる。閉じる位置は直前の代入に対応する。'
    if s.startswith('for '):
        return '並びの要素を順番に取り出すループ。次の字下げブロックを要素ごとに実行する。'
    if s.startswith('while '):
        return '条件が真の間繰り返す。状態が進む処理と終了条件の組合せを確認する。'
    if s.startswith('or not request_parts[1]'):
        return '要求行の第2要素であるtargetが空でないことと、第3要素がHTTP/1.1であることを継続して検査する。'
    if s.startswith('if ') or s.startswith('elif '):
        return '条件を評価し、真であれば次の字下げした処理へ進む。偽ならこの分岐は実行しない。'
    if s.startswith('else:'):
        return '直前の条件が満たされなかった場合に実行する分岐。'
    if s.startswith('with '):
        return '一時的に使う資源をwithの範囲へ閉じ込める。抜ける際の後片付け方法は対象オブジェクトに依存する。'
    if s == 'break':
        return '最初の空行を見つけたため、ヘッダーを読むforループを終えます。後続の本文は解析対象へ混ぜません。'
    if s.startswith('continue'):
        return '今回の繰り返しの残りを飛ばし、次の要素へ進む。'
    if s.startswith('#'):
        return 'この行はコメント。実行されないが、安全上の制約や教材専用の意図を明記する。'
    if 'sys.argv' in s:
        return 'コマンドで渡された文字列の個数や位置を確かめる。添字を読む前に引数の数を検査する。'
    if 'len(' in s:
        return '要素数・文字数・バイト数のいずれを数えているかは対象による。ここの制限は不正入力や過大入力対策。'
    if s.endswith('= []'):
        return f'{s.split("=",1)[0].strip()}に空のリストを割り当てる。後続のappendなどで要素を増やす初期化。'
    if s.endswith('= {}'):
        return f'{s.split("=",1)[0].strip()}に空の辞書を用意する。後続でキーと値の対応を格納する。'
    if '.get(' in s:
        return '辞書のgetでキーを探す。キーが無いときは指定の既定値を返し、KeyErrorを避ける。'
    if ' = ' in s:
        name, expr = s.split(' = ',1)
        return f'右側の式「{expr}」を評価し、得られた値を{name.strip()}へ代入する。この値が後続の判定・表示の入力になる。'
    if s.endswith(')') and '.' in s:
        return f'「{s}」を呼び出す。ドットの右側は対象オブジェクトの処理を指定する。'

    return 'この文は直前の条件や関数の文脈で評価される。変数の現在値と字下げを確認して実行順を追う。'


def line_breakdown(n, number, line):
    """Provide the semantic note AND an explainer for each lexical component."""
    statement = p(esc(note_for(n, line)), 'statement-explanation')
    parts = explain_line(line, LEX[n].get(number, []))
    if not parts:
        return statement + p('この行のトークンは次の物理行と連続します。字下げ・対応する括弧も確認してください。')
    return statement + '<details class="syntax-segment"><summary>この行の記号・名前・値を分解して読む</summary>' + p(esc(parts), 'token-explanation') + '</details>'


def full_table(n, lines):
    rows = []
    for k, line in enumerate(lines, 1):
        if not line.strip():
            continue
        rows.append(f'<tr><td><a href="#src{n:02d}-L{k}">{k}</a></td><td><code>{esc(line)}</code></td><td>{line_breakdown(n,k,line)}</td></tr>')
    return '<div class="table-wrap"><table><thead><tr><th>行</th><th>Pythonコード</th><th>動きと、その行の構文要素を1つずつ説明</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def step_explanation_table(n, lines, start, end):
    rows=[]
    for index in range(start,end):
        if lines[index].strip():
            line = lines[index]
            rows.append(f'<tr><td><a href="#src{n:02d}-L{index+1}">{index+1}</a></td><td><code>{esc(line.rstrip())}</code></td><td>{line_breakdown(n,index+1,line)}</td></tr>')
    return '<div class="table-wrap"><table><thead><tr><th>行</th><th>実際のコード</th><th>具体的な動作と構文分解</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def table(headers, rows):
    result = '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{esc(h)}</th>' for h in headers) + '</tr></thead><tbody>'
    for row in rows:
        result += '<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in row) + '</tr>'
    return result + '</tbody></table></div>'


def chapter(chap_id, title, body):
    return (f'<section class="chapter" id="{chap_id}" tabindex="-1" data-title="{esc(title)}"><h2>{esc(title)}</h2>{body}' +
            f'<label class="check"><input type="checkbox" data-check="{chap_id}"/>この章を確認した</label></section>')


_observed_cache = {}


def observed(commands):
    # Run each published example once per generator process. No user commands.
    key = tuple(commands)
    if key not in _observed_cache:
        result = subprocess.run('\n'.join(commands), cwd=ROOT, shell=True,
                                capture_output=True, text=True, timeout=12,
                                executable='/bin/bash')
        _observed_cache[key] = (result.stdout, result.stderr, result.returncode)
    return _observed_cache[key]


def make():
    css = (ROOT / 'verification' / 'style_base.css').read_text(encoding='utf-8')
    css += '\n.output-example{border-left:4px solid var(--lime);background:#1a2821;padding:18px;margin:18px 0}.danger-note{border-left:4px solid var(--orange);background:#28231c;padding:14px 20px}.codebox pre code .line{display:inline;white-space:pre}.step .quick{font-size:.91rem;color:#b7c9d1}.source-section{margin:22px 0;padding:16px;border:1px solid var(--line)}.source-section summary{font-weight:bold;color:var(--cyan)} .chapter>.check{margin-top:32px}.muted{color:#b9c5ca}.table-wrap code{white-space:pre-wrap}.hero strong{color:var(--lime)}.subtitle{color:var(--cyan);font-weight:600}.badge-note{color:var(--orange)} #toc .group{font-weight:700;color:var(--orange);margin:12px 10px 7px;font-size:.76rem} .step>a{font-size:.85rem} .source-section pre{max-height:70vh} .table-wrap{overflow-x:auto}.table-wrap table{min-width:620px}.codebox pre code{white-space:pre} .step{background:#151f24} .focus main{max-width:1140px} @media print{.chapter{break-before:page}.step,.source-section{break-inside:auto}}'
    css += '\n.syntax-segment{margin:8px 0 2px;padding:8px;border-color:#49606a;background:#172126}.syntax-segment summary{font-weight:500;color:#b8e3e6}.token-explanation{font-size:.83rem;line-height:1.9;white-space:normal;overflow-wrap:anywhere}.statement-explanation{margin:0 0 6px}.table-wrap td:nth-child(1){white-space:nowrap}.table-wrap td:nth-child(2) code{white-space:pre-wrap;overflow-wrap:anywhere}.table-wrap table{min-width:620px}.syntax-segment[open]{max-width:100%;}.syntax-segment p{max-width:100%;}@media(max-width:600px){.syntax-segment{padding:7px}.token-explanation{font-size:.78rem}}'
    labels = [('cover','01 表紙と10作品'),('usage','02 本書の使い方'),('setup','03 Linuxとvimの準備'),('basics','04 セキュリティ実習の基本'),('schedule','05 12時間以内の学習計画')]
    labels += [(f'p{i:02d}',f'{i+5:02d} {d["title"]}') for i,d in enumerate(DATA,1)]
    labels += [('trouble','16 トラブルシューティング'),('glossary','17 用語と判断の目安'),('references','18 公式参考資料'),('appendix-a','19 完成ソースと逐行解説'),('appendix-b','20 検証と制約の一覧')]
    nav = '<p class="group">導入と準備</p>' + ''.join(f'<a href="#{k}">{esc(v)}</a>' for k,v in labels[:5])
    nav += '<p class="group">実習 01〜10</p>' + ''.join(f'<a href="#{k}">{esc(v)}</a>' for k,v in labels[5:15])
    nav += '<p class="group">困ったとき・付録</p>' + ''.join(f'<a href="#{k}">{esc(v)}</a>' for k,v in labels[15:])
    parts = []
    index = [(f'{i:02d}', d['title'],str(d['mins'])+'分') for i,d in enumerate(DATA,1)]
    cover = f'''<div class="hero"><p class="eyebrow">OFFENSIVE SECURITY · CLOSED LAB / 2026-11-11</p><h1>攻撃者視点で学ぶ<br>Pythonペンテスト10作品</h1><p>偵察、攻撃入力、結果の証拠、対策の比較を、小さな自作ツールで学びます。添付教材のダークテーマ・左目次・検索・行番号・4工程・コードコピーを継承し、各工程と付録Aで実行行すべての日本語解説を付けています。</p><div class="stats"><div><strong>10作品</strong>独立した演習</div><div><strong>600分</strong>学習＋実装＋逐行確認</div><div><strong>12時間</strong>予備時間まで含む計画</div><div><strong>追加導入なし</strong>外部依存なし</div></div></div>'''
    cover += p('ここでの攻撃対象は、自分で作る架空のデータ・SQLiteメモリDB・127.0.0.1上のデモサーバーだけです。攻撃者の操作を学ぶためunsafe実装が登場しますが、他人のシステムを対象とする仕組みではありません。')
    cover += p('学習の基本サイクルは、対象を読む→攻撃仮説を立てる→ペイロードを入力する→観測結果を記録する→safe実装と比較する、です。脆弱性の検証にならない静的な偵察作品は「疑い」と「実証」を区別します。')
    cover += table(['番号','題材','基本実習'], index)
    cover += '<div class="danger-note"><strong>学習の範囲</strong><p>外部ドメインを対象にしたポート走査や認証試行、第三者のログ・Cookie・秘密鍵の使用は禁止。04・05・06・07・08には、比較実験用の弱い振る舞い・危険な例が含まれます。学習用のメモリDBから外へ流用しないでください。ネットワークを使う03も127.0.0.1固定です。</p></div>'
    cover += p('完成条件は各章のSTEP 01〜04を自分で入力し、コマンドの出力を照合し、攻撃者が与えた入力・観測した事実・成立する原因・防ぎ方を自分の言葉で説明すること。各工程の全行解説を読みながら進める想定です。')
    parts.append(chapter('cover',labels[0][1], cover))

    usage = p('各作品は独立したスクリプトです。前の作品が動かなくても、次へ進めます。章内のSTEP 01〜04を1つのpractice/*.pyへ上から順に追記すると、projects/内の完成版とバイト単位で一致する構成です。途中は未完成のため、STEP 04を終えてから実行します。')
    usage += table(['場所','内容と注意'], [('Python_ペンテスト10作品_全行構文分解_20261111.html','現在読んでいるHTML。ローカルブラウザーだけで読める。'),('projects/','10作品の照合用完成Pythonコード。'),('practice/','自分で入力する場所。空のフォルダーから始める。'),('samples/','入力用の合成サンプル。実物の機密ログやCookieを含まない。'),('tests/test_all.py','標準unittestによる回帰テスト。'),('verification/','HTMLと完成ソースの一致検査、テストログ、作成時の実行記録。'),('PROJECT_HISTORY.json','添付の参考教材と今回の題材の重複管理。')])
    usage += p('コードの左の行番号は説明用で、コピーするときには含まれません。コード欄の「コピー」がブラウザー権限で失敗した場合は手動コピー欄から選択します。コピーできる箇所は本文・工程・付録のコードすべてです。')
    usage += p('左目次で章を切り替えます。Ctrl+Kで全文検索、A−/A＋で表示倍率、折り返しで長い行の表示、集中表示で目次の非表示を切り替えます。チェックと表示設定の保存はブラウザーに許可されるときだけ端末内へ保持します。JavaScriptが無効なら全章が続けて表示されます。')
    usage += p('すでにSTEP 01〜04を入力したファイルへ、付録Aの完成コードをさらに追加しないでください。完成版を一括コピーするならpracticeの中身を丸ごと置き換えます。')
    parts.append(chapter('usage',labels[1][1],usage))

    zip_name = 'Python_Offensive_Pentest_10Labs_20261111_36additional_checks_refined.zip'
    root_name = 'Offensive_Python_10Labs_Review68_20261111'
    setup = p('Arch Linux、Linux Mint、Kali Linuxの標準的な端末操作を想定しています。Python 3.10以上、vimまたはNeovim、ローカルブラウザーがあれば使えます。教材は標準ライブラリのみで、インストールが済めばインターネット不要です。')
    setup += block('python3 --version\npwd\n', 'bash · Pythonと現在地の確認','setup-check')
    setup += p('Pythonがない場合だけパッケージ管理で導入します。Archでは'+inline('sudo pacman -S python vim')+'、Mint/Kaliでは'+inline('sudo apt update')+'の後に'+inline('sudo apt install python3 vim')+'が例です。環境の公式パッケージ管理方針に従ってください。')
    setup += block(f'cd ~/Downloads\npython3 -m zipfile -e {zip_name} .\ncd {root_name}\npwd\nls\n', 'bash · ZIPを展開（Downloadsにある場合）', 'setup-unzip')
    setup += p('ここからの'+inline('projects/')+'・'+inline('samples/')+'は、いまいる教材ルートからの相対パスです。HTMLを開いただけではターミナルの現在地は移動しません。')
    setup += block('mkdir -p practice\nvim practice/01_header_audit.py\n','bash · 自分の実習ファイルを開く','setup-vim')
    setup += p('vimを開いたら i で挿入モード、各工程のコードを上から入力、Esc → :wq → Enterで保存終了。編集を続けるときはEsc → G → oで末尾の次行へ進みます。Neovimならvimをnvimに置き換えます。Pythonでは4スペースのインデントを使い、タブと混ぜません。')
    setup += block('python3 practice/01_header_audit.py samples/response_headers.txt https\necho $?\ndiff -u projects/01_header_audit.py practice/01_header_audit.py\n','bash · 保存後の実行と完全比較','setup-run')
    setup += p('echo $?は直前のコマンドの終了ステータスで、通常成功0・操作不能1・使い方の誤り2としています（学習コードの規約）。diff -uはバイトや空白の差を行単位で示します。+/-の行が出たら、4スペースと末尾改行を含め見直してください。cmpは最初に違うバイト位置を知るのに便利です。')
    parts.append(chapter('setup',labels[2][1],setup))

    basics = p('セキュリティツールを書くとき、値の型・入力源・許可境界を区別できることが重要です。Pythonの構文を「何のデータに適用しているか」とセットで読んでいきます。')
    basics += table(['用語・構文','この教材の具体例'], [('str','sys.argv[1]で受け取るファイル名やユーザー名。文字列は数字に見えても自動では数値にならない。'),('bytes','PCAPやHTTP/1.1のCRLFなど、バイト列として扱うデータ。strとは別の型。'),('dict','キーと値の対応。HTTPヘッダー名→値一覧やユーザー名→ロールを保持する。'),('list','値を順番に保持する配列のような容器。notes.appendで末尾に注意文を追加する。'),('tuple','(name,)は1要素の組。sqlite3へ1個の値をパラメーターとして渡すときに使う。'),('if / elif / else','許可する条件と拒否する条件を順番に判断する。4スペースの字下げが範囲を決める。'),('try / except','ファイルがない、形式がおかしいなど想定した失敗を、長い例外表示にせず説明する。'),('def / return','処理を関数で定義し、関数を終えるときに値を返す。printとは異なる。'),('arg / sys.argv','コマンドラインの引数。[0]はスクリプト名、[1]以降は入力値。'),('pathlib.Path','ファイル位置を表現する。resolveで実体パスへ変換するが、競合問題には注意。'),('安全な条件判定','全てのエラーや未知入力を黙って許可しない。明示的な条件を満たしたときだけ認可する。')])
    basics += block('items = ["alice", "bob"]\nfor name in items:\n    if name == "alice":\n        print(name, "ALLOW")\n    else:\n        print(name, "DENY")\n', 'python · 保存して試せる基礎例','basics-example')
    basics += p('ループ1回目はname="alice"なので==がTrueになりALLOW、2回目はname="bob"なのでFalseになりDENYです。条件の中に入りたい場合だけ4スペース深くします。')
    basics += p('記号の読み分けが大切です。=は値の代入、==は比較、:はif・for・defの本文開始や辞書の区切りです。[]はリストの作成にも要素アクセスにも使われ、()は関数呼び出しや式のグループ化に使います。同じ記号でも文脈で意味が変わるため、行の説明と合わせて読みます。')
    basics += table(['構文','実際の意味','ミニ例'], [('a = 3','代入。aという名前に整数3を結び付ける','a = 3'),('a == 3','比較。等しければTrue','if a == 3:'),('args[1]','リストargsの添字1（2番目）','sys.argv[1]'),('name.lower()','nameのlowerメソッドを呼び出す','name.lower()'),('len(data)','dataの要素数を返す関数の呼び出し','len(data)'),('f"value={value}"','波括弧の中の式を埋め込んだ文字列','f"value={value}"'),('b"\\r\\n"','文字列ではなくバイト列でCRLFを表す','b"\\r\\n"')])
    basics += p('strとbytesの違いにも注意してください。たとえば"abc"はstrで、b"abc"はbytesです。前者の長さは文字単位、後者はバイト単位です。HTTP/1.1の長さやPCAPのoffsetはバイト数なので、文字列へ先に変換すると境界を取り違える危険があります。')
    basics += '<div class="danger-note"><strong>権限のない対象は試さない</strong><p>03の対象はコード内で127.0.0.1に固定。05の脆弱なSQLは外部接続しないインメモリDB限定。その他は保存済み教材ファイルの処理です。検査対象の同意が必要という原則は、ネット上のツールと同じです。</p></div>'
    parts.append(chapter('basics',labels[3][1],basics))

    schedule = p('10作品の実習時間は合計600分。これはPythonソースを自分で入力・保存・実行し、STEP内の全非空行の説明を読み、攻撃入力と観測結果を1つずつ確認する時間の目安です。さらに準備・休憩・見直しで100分を取ります。')
    schedule += table(['区間','内容','目安'],[('準備','Python確認・展開・vim操作と安全範囲の確認','25分'),('前半','01〜05：偵察、通信探索、パス・SQL入力','275分'),('休憩','小休止と食事を合計','45分'),('後半','06〜10：認証、トークン、IDOR、PCAP、HTTP','325分'),('見直し','差分比較・テスト・攻撃と防御の記録','30分'),('合計','コード全行の確認を含む基本ルート','700分（約11時間40分）'),('予備','境界入力を再度試す余裕','20分')])
    schedule += p('600+25+45+30+20=720分で12時間の計画です。初学者が詰まる場合もあるため、所要時間は保証ではありません。追加実験を全種類試す作業や公式資料の通読は基本枠には含めません。')
    parts.append(chapter('schedule',labels[4][1],schedule))

    for n,(d,path) in enumerate(zip(DATA,FILES),1):
        data = path.read_text(encoding='ascii')
        lines = data.splitlines(keepends=True)
        assert len(d['steps']) == 4
        cuts = [0] + d['cuts'] + [len(lines)]
        assert cuts == sorted(cuts)
        composed = ''.join(''.join(lines[a:b]) for a,b in zip(cuts,cuts[1:]))
        assert composed == data, (n,'chunks differ')
        name = path.name
        body = p(f'<strong>{esc(d["english"])} / 約{d["mins"]}分</strong><br>{esc(d["desc"])}', 'subtitle')
        body += f'<div class="note"><strong>セキュリティで何が分かるか</strong><p>{esc(d["output"])}</p></div>'
        body += p(f'<strong>教材としての限界：</strong>{esc(d["limits"])}')
        body += '<div class="card"><p class="eyebrow">攻撃者側の検証シナリオ</p>'
        body += p(f'<strong>想定される攻撃側の狙い：</strong>{esc(d["attacker"])}')
        body += p(f'<strong>この作品で実際に試すこと：</strong>{esc(d["action"])}')
        body += p(f'<strong>観察できればよい証拠：</strong>{esc(d["evidence"])}')
        body += p(f'<strong>防御側が行うこと：</strong>{esc(d["mitigation"])}')
        body += '</div>'
        body += p(f'<strong>攻撃工程の位置づけ：</strong>{esc(d["phase"])}。{esc(d["purpose"])}')
        body += '<h3>初学者向け：この作品の仕組みを具体例から理解する</h3>'
        for key, explanation in BEGINNER[n]:
            body += f'<div class="card"><h4>{esc(key)}</h4><p>{esc(explanation)}</p></div>'
        body += '<details><summary>発展解説：実装とセキュリティ仕様をさらに掘り下げる（任意）</summary>'
        for title, explanation in DEEPER[n]:
            body += f'<div class="card"><h4>{esc(title)}</h4><p>{esc(explanation)}</p></div>'
        body += '</details>'
        body += p('Pythonのコードは「入力を受け取る → 型を確かめる → 条件を評価する → 出力する」の順で追います。STEP内の表で各行を確認した後、「この行の記号・名前・値を分解して読む」を開いて、=、==、:、.、[]、()、文字列と変数などの働きを個別に照合できます。字下げ4個はブロックの階層であり、コピー時に行番号は入りません。')
        body += '<h3>作る前に理解する用語</h3><dl>'
        for term,definition in d['terms_extra']:
            body += f'<dt>{esc(term)}</dt><dd>{esc(definition)}</dd>' 
        for term, definition in d['terms']:
            body += f'<dt>{esc(term)}</dt><dd>{esc(definition)}</dd>'
        body += '</dl>'
        body += p(f'<strong>実習ファイル：</strong>{inline("practice/"+name)}　／　<strong>完成版：</strong>{inline("projects/"+name)}')
        body += block(f'mkdir -p practice\nvim practice/{name}\n', 'bash · vimで実習先を作る',f'open-{n:02d}')
        body += p('STEP 01〜04は同じファイルへ順番に追記します。コード番号は入力せず、空行とインデントも残してください。STEP 04が終わるまでは実行しません。')
        for part,(a,b) in enumerate(zip(cuts,cuts[1:]),1):
            title,desc = d['steps'][part-1]
            chunk = ''.join(lines[a:b])
            body += f'<article class="step" id="p{n:02d}-step{part}"><p class="eyebrow">STEP {part:02d} / 04 · lines {a+1}–{b}</p><h3>{esc(title)}</h3>'
            body += p(esc(desc))
            body += p(f'<strong>入力位置：</strong>{"ファイルの先頭" if part==1 else "前の工程の直後（同じファイル）"}。完成版{a+1}〜{b}行に対応。')
            body += f'<a href="#src{n:02d}-L{a+1}">付録Aの該当行と説明を見る</a>'
            body += block(chunk,f'{name} · STEP {part:02d}',f'p{n:02d}-chunk{part}',True,a+1)
            begin = [x for x in range(a,b) if lines[x].strip()]
            body += '<details><summary>STEP内の全コード行を解説（クリックで1行の記号・名前・値まで展開）</summary>'
            body += step_explanation_table(n, lines, a, b)
            body += '</details>'
            if part < 4:
                body += p('この段階はコードの途中です。保存・実行せず次のSTEPへ続けます。','quick')
            else:
                body += p('これで1ファイルが完成。Esc → :wq → Enterで保存し、次の基本例を実行します。','quick')
            body += '</article>'
        body += '<h3>実行して答え合わせをする</h3>'
        body += block('\n'.join(d['cmd'])+'\n', 'bash · 教材ルートから実行',f'run-{n:02d}')
        out, err, rc = observed(d['cmd'])
        if n==3:
            out = re.sub(r'Local demo port: \d+', 'Local demo port: （実行時にOSが割り当てた番号）', out)
        if n==7:
            out = out.replace('VALID user=alice role=viewer','VALID user=alice role=viewer')
        assert rc in (0,1) and not err, (n,rc,err)
        body += block(out, 'stdout · 保存済み完成版を実行して確認',f'out-{n:02d}')
        if n==4:
            body += p('1つ目は教材secret.txtの読出しに成功し終了0、2つ目は公開ルート外で拒否され終了1です。教材samples外はどちらのモードでも拒否します。')
        elif n==7:
            body += p('最後のverifyは意図的にINVALIDとなり終了1です。途中のinspectは検証していない内容を表示するだけで、認証の成功ではありません。')
        elif n==3:
            body += p('ポート番号はOSが毎回選ぶため、実行するたびに変わります。数値ではなくOPENとLAB SERVICEという確認点を照合します。')
        else:
            body += p('コマンドの表示結果と比較します。正常な検査結果を表示できた場合の終了ステータスは0です。判定がREVIEWやDENYであっても、処理の成功と判定結果は別です。')
        body += '<h3>変数を追う：目に見えない途中の値</h3>' + table(['段階','具体的な入力・値','理由と次の動作'],d['trace'])
        # An extra source-anchored walkthrough for three security-critical expressions per lab.
        body += '<h3>重点30行の構文分解：入力・演算・戻り値を追いかける</h3>'
        body += p('各作品から3つの重要な実コード行を選び、演算子・関数・引数・結果を4つの単位に分解しました。先ほど自分で入力したコードと照らしてください。')
        deep_rows = []
        for item in WALKTHROUGHS[str(n)]:
            matched = [(pos, text) for pos, text in enumerate(lines, 1) if item['anchor'] in text]
            assert len(matched) == 1, (n, item['anchor'], matched)
            line_number, complete = matched[0]
            deep_rows.append((str(line_number), complete.strip(), ' ／ '.join(item['pieces']), item['caution']))
        body += table(['行','実コード','4段階で読み解く','実際に注意すること'], deep_rows)

        if n == 1:
            body += '<h3>追加の境界条件：空値とヘッダー・本文の境目</h3>'
            body += p('HTTPのフィールド値そのものは空でも構文上許されます。CSPなど空値の設定は意味を確認する必要があります。読み取りは最初の空行で止めるため、その後にある文字列をヘッダーとして検査しません。単独CR・NUL文字は入力エラーになります。')
            body += p('確認用の短い例はテストtest_01_empty_field_is_valid_but_empty_policy_is_not_a_passとtest_01_bare_cr_and_invalid_status_line_rejectedで自動実行できます。')
        elif n == 2:
            body += '<h3>追加精査：改行文字がCookie行を偽装する問題</h3>'
            body += p('\r（CR、0x0d）と\n（LF、0x0a）は別のバイトです。CRLFなら通常の行末として扱いますが、単独CRをsplitlinesで勝手に別行として解釈すると、意図しない別のSet-Cookie行が作られたように見えます。保存ファイルをbytesで読み、CRLFを取り除いてなお残るCRを拒否します。')
            body += p('対応する追加試験：test_02_lone_cr_in_saved_header_rejected / test_02_normal_lf_and_crlf_remain_supported。改行の検査はCookieの安全性そのものを証明するものではありません。')
            body += '<h3>追加の境界条件：引用符とCookie値</h3>'
            body += p('Set-Cookie: id="abc"; Secureでは両端の引用符をはがして値の文字集合を確認します。Set-Cookie: id="abc; Secureのように片側だけの場合は、引用符を勝手に補わず入力エラーにします。')
        elif n == 3:
            body += '<h3>追加精査：ポート文字列は整数変換前に制限する</h3>'
            body += p('ポート番号の最大値は65535です。たとえばcheck 65536は範囲外で拒否します。極端に長い数字列を先にintへ渡すと処理負荷やPythonバージョンによる桁数制限の影響があるので、まず長さ8文字以内を確かめます。この8文字は入力の上限で、ポートの許可範囲は引き続き1〜65535です。')
            body += '<h3>追加の境界条件：接続と受信の成功を混同しない</h3>'
            body += p('TCPの接続確立後でもrecv()が例外になることはあります。この場合は接続自体の結果OPENを保ち、バナー欄にbanner read failedを表示します。対してcreate_connectionの失敗はCLOSED/UNREACHABLEです。実サービスへの脆弱性の有無を直接判断する道具ではありません。')
        elif n == 7:
            body += '<h3>追加精査：Base64URLの見た目が異なっても同じバイトになる</h3>'
            body += p('Base64URLは暗号化ではなく表記変換です。末尾のパディング（=）を省き、A〜Z、a〜z、0〜9、ハイフン、アンダースコアのみを認めます。復号後に再度encodeして元の文字列と一致するかを確認し、例えばe30（{}という2バイト）と同じ値に復号できる非正規形e31を拒否します。署名チェックとは別の入力形式検査です。')
            body += '<h3>追加の境界条件：MACの正しさと権限の正しさ</h3>'
            body += p('この教材のLAB_KEYはコードを読めば誰でも分かる固定の鍵です。その鍵を知る人はadminを含むデータにも正しいHMACを付け直せます。verifyはユーザー名とroleの型・長さなど最低限の構造を検査しますが、adminという役割を許可してよいかは判断しません。verifyの成功は「その鍵で作られたMACが一致し、最低限の構造に合う」という意味であり、アプリの認可や鍵の秘匿まで証明しません。')
        if n == 10:
            body += '<h3>追加精査：本文を検査していないのに安全と表示しない</h3>'
            body += p('Transfer-Encoding: chunkedが書かれていても、教材はチャンク長・末尾の0チャンク・トレーラーの整合性を解析しません。したがって本文が未検証である旨をREVIEWとして出します。またCL/TEのどちらも無いのにヘッダー後ろにバイトが残る場合もREVIEWです。単純なGETや長さが一致したContent-Lengthの例まで誤って警告しないこともテストで確認します。')
        body += '<h3>正常系と異常系を自分で確認</h3>'
        bad = ['引数なしで実行 → Usageと終了ステータス2','指定ファイルが存在しない → Errorと終了ステータス1']
        if n==3:bad=['引数なし → Usageと2','check 0 → 範囲エラーと2','demo → OPENと0']
        if n==4:bad=['safe public.txt → 公開ファイルを表示','unsafe ../secret.txt → 合成秘密データを表示','safe ../secret.txt → 拒否と終了1','unsafe /etc/passwd → 教材samples外なので拒否と終了1']
        if n==6:bad=['unprotected → 4回照合','protected → 最初の2回だけ照合し3人目と4人目はBLOCKED','引数なし → Usageと2']
        if n==5:bad=['引数なし → Usageと2','safe alice → aliceに一致','unsafeの学習用文字列 → 2件一致']
        if n==7:bad=['create alice viewer → トークン生成と0','tamper TOKEN admin → データの権限だけを書換','inspect FORGED → UNTRUSTEDでadmin表示','verify FORGED → INVALIDで1']
        if n==8:bad=['unsafe alice notes read → ALLOW','safe alice notes read → DENY','safe bob notes edit → ALLOW','safe alice notes delete → 不正操作と2']
        body += '<ul>'+''.join(f'<li>{esc(x)}</li>' for x in bad)+'</ul>'
        body += f'<div class="note"><strong>追加実験（時間外でも可）</strong><p>{esc(d["experiment"])}</p></div>'
        body += '<div class="danger-note"><strong>よくある誤解と注意</strong><p>'+esc(d['gotcha'])+'</p></div>'
        body += p(f'<strong>完成版と同じか確認する：</strong>{inline("diff -u projects/"+name+" practice/"+name)}')
        body += p('差分が無ければdiff -uは何も表示せず終了ステータス0。差分があれば該当する工程の空白・引用符・変数名を調べます。')
        parts.append(chapter(f'p{n:02d}',labels[n+4][1],body))

    trouble = table(['症状','確認と修正'],[
        ('python3: command not found','Pythonがインストールされているか、python3 --versionで調べる。'),
        ('FileNotFoundError','pwdとlsで現在地を確認。サンプルの相対パスは教材ルートが基準。'),
        ('IndentationError','行頭スペースを4/8/12個に揃え、タブを混ぜない。'),
        ('SyntaxError','コロン、括弧、引用符を確認。STEP 04まで入力したかを確認。'),
        ('diffが大量に出る','diff -uで空白差を含む行を見つける。vimの:set listでタブや行末空白も確認。'),
        ('03のdemo番号が違う','仕様通り。ポート0でOSが空きポートを割り当てる。'),
        ('04がBlocked','safeの公開ルート外拒否は想定どおり。unsafeでも教材samplesの外や絶対パスは拒否される。'),
        ('07のINVALID','FORGEDのverifyは期待される失敗。元のTOKENのverifyがVALIDかも確かめる。'),('07のBase64URLエラー','パディング=・標準Base64の+/・非正規形を拒否する。元のcreate結果で再試行する。'),
        ('09がPCAP形式エラー','教材はclassic PCAPのみ。WiresharkのPCAPNGを直接読む機能はない。'),
        ('10で警告が出ない','保存サンプルにCRLFがあるか確認。chunked本文の未検証は必ずREVIEW。'),
        ('ブラウザーでコピーできない','file://ページではクリップボード権限が制限されることがある。手動コピー欄から選択。'),
    ])
    trouble += p('どの作品でも「期待した結果を得られなかった」ときは①実行したコマンド②現在地pwd③入力の中身④終了ステータスecho $?⑤完成版との差分、という順序で切り分けると誤解が減ります。')
    parts.append(chapter('trouble',labels[15][1],trouble))
    glossary = table(['概念','説明と参照箇所'],[('誤検知','見つかった兆候が直ちに攻撃を意味しない。01,02,06,10。'),('脆弱性','攻撃につながる弱点のこと。単なる警告や未実装の機能とは区別する。'),('認証 / 認可','本人や主体を確かめること / 操作の許可を判断すること。06と08。'),('合成データ','実在の利用者や通信とは無関係に作った練習材料。06と09。'),('タイムアウト','待ち続けないための時間制限。03。'),('HMACとハッシュ','HMACは鍵を使う認証コード。一般のファイルハッシュとは用途が異なる。07。'),('PCAP','パケットのデータを保存する形式。09。'),('RFC','通信プロトコルなどの仕様を文書化する規格群。10。'),('最小権限','目的に必要な操作だけを許可する設計。04と08。'),('ディレクトリトラバーサル','許されたルート外へパスを移動しようとする入力。04。')])
    parts.append(chapter('glossary',labels[16][1],glossary))
    refbody = p('添付教材はレイアウト・説明順序の参考です。技術仕様の根拠はPython公式資料とOWASP / RFCの公開文書を併記します。本文はこれらの長文引用を含まず、今回の学習範囲に合わせて書いています。')
    refbody += '<ul>' + ''.join(f'<li><a href="{esc(url)}">{esc(title)}</a></li>' for title,url in REFS) + '</ul>'
    refbody += p('RFC 9112ではHTTP/1.1の送信形式としてCRLFを要求し、受信側で単独LFを許容する余地も認めています。作品10は解析者による解釈差を避けるため厳格なCRLFを採用しています。作品02はRFC 6265のCookie処理を参照します。')
    refbody += p('HTTPヘッダーやCookieの防御効果は環境・ブラウザー・設定の組合せによります。本教材の出力は検査の入り口であり、OWASPの各項目を使って設計要件を改めて確認してください。')
    parts.append(chapter('references',labels[17][1],refbody))
    appendix_a = p('STEP 01〜04を連結したものと一致する完成ファイル全文です。全非空行に実行時の役割と、各トークン（名前・関数・記号・文字列・数値）を個別に説明する折り畳み欄を用意しました。説明は実際のソースから字句解析して作っています。字句分解は処理の安全性や型推論を保証するものではありません。')
    for i,path in enumerate(FILES,1):
        source = path.read_text(encoding='ascii')
        digest = hashlib.sha256(source.encode('ascii')).hexdigest()
        appendix_a += f'<details class="source-section" id="source-{i:02d}"><summary>{i:02d} {esc(path.name)} （{len(source.splitlines())}行）</summary>'
        appendix_a += p(f'SHA-256: {inline(digest)}')
        appendix_a += block(source, f'projects/{path.name} · 完成ソース', f'src{i:02d}',True,1)
        appendix_a += '<h3>非空行の逐行説明</h3>' + full_table(i,source.splitlines())
        appendix_a += p(f'<a href="#p{i:02d}-step1">作品{i:02d}のSTEP 01へ戻る</a>')+'</details>'
    parts.append(chapter('appendix-a',labels[18][1],appendix_a))

    append_b = p('以下の検証方法は実際の作品とマニュアルの一致を確認するためのものです。自動テストは全入力・全ディストリビューションでの動作を保証するものではありません。')
    append_b += block('python3 tests/test_all.py\npython3 verification/verify_manual.py\npython3 verification/audit_30_checks.py\npython3 verification/audit_24_new.py\npython3 verification/audit_32_additional_rounds.py\npython3 verification/audit_36_more_rounds.py\npython3 tests/test_revision.py\n', 'bash · 自動テストと教材一致検査','test-b')
    append_b += table(['観点','確認方法'],[('Python構文','compileallまたはpy_compileで10作品を構文解析。'),('実際の動作','unittestで入力境界・代表正常系・異常系を確認。'),('同梱内容','samplesに実行例と同じ名前のファイルが存在すること。'),('本文のコード','工程01〜04を連結して完成ソースと一致すること。'),('付録A','行番号付き完成コードがファイル全文と一致すること。'),('ASCII規約','projects/*.py内がASCIIだけであること。'),('安全な範囲','03はHOST固定、04のunsafeもsamples外を禁止、05はメモリDB、06/08は架空データのみ。'),('閲覧操作','Chromiumのローカル表示でJavaScriptエラーの有無と章切り替えを確認。')])
    append_b += p('今回の改訂では、10作品のうち4作品の関数内部へモード名の明示チェックを追加し、署名付きトークンの型・長さ検査を追加しました。全非空行の字句分解解説を維持し、30の重要なソース行について120の個別構成要素を詳解しました。以前の32観点点検に加え、新しい36観点の再点検を実施します。点検は自動照合であり、専門家による36人分の監査や全入力を保証するものではありません。')
    append_b += p('既存の添付教材からは形式・配色・解説方式のみを参考にしました。前の教材に登場したファイルハッシュ、IP判定、単語検索といった課題を、そのまま今回の作品として流用していません。')
    append_b += p('実行例はこのパッケージ内の完成コードとサンプルを組み合わせて生成しています。機械の状況に依存する03のポート番号だけは「実行時に割り当てた番号」と表記しています。')
    parts.append(chapter('appendix-b',labels[19][1],append_b))

    js = r'''<script>
(function(){
  document.documentElement.classList.add('js');
  const sections=[...document.querySelectorAll('.chapter')];
  const links=[...document.querySelectorAll('nav a[href^="#"]')];
  const store='offensive-python-pentest-labs-20261111-68round';
  let state={done:{},scale:1,wrap:false,focus:false};
  try {const saved=localStorage.getItem(store);if(saved){const parsed=JSON.parse(saved);if(parsed && typeof parsed==='object'){if(parsed.done && typeof parsed.done==='object' && !Array.isArray(parsed.done))state.done=parsed.done;if(Number.isFinite(parsed.scale))state.scale=Math.max(.85,Math.min(1.4,parsed.scale));state.wrap=parsed.wrap===true;state.focus=parsed.focus===true;}}}catch(e){}
  function persist(){try{localStorage.setItem(store,JSON.stringify(state));}catch(e){document.getElementById('storage-status').textContent='保存できない環境です。チェックはこの画面内だけ有効です。';}}
  function drawProgress(){
    let done=0;
    sections.forEach(sec=>{const cb=sec.querySelector('[data-check]');if(!cb)return;cb.checked=Boolean(state.done[sec.id]);if(cb.checked)done++;});
    document.getElementById('progress').textContent=done+' / '+sections.length+'章 完了';
  }
  function sizeHeader(){document.documentElement.style.setProperty('--head',document.querySelector('header').getBoundingClientRect().height+'px');}
  function drawDisplay(){document.documentElement.style.setProperty('--scale',state.scale);document.body.classList.toggle('wrap',state.wrap);document.body.classList.toggle('focus',state.focus);document.getElementById('wrap').setAttribute('aria-pressed',String(state.wrap));document.getElementById('focus').setAttribute('aria-pressed',String(state.focus));sizeHeader();}
  function active(){
    const target=decodeURIComponent(location.hash.slice(1));const node=document.getElementById(target);
    const section=node?.closest('.chapter')||sections[0];
    sections.forEach(item=>item.classList.toggle('active',item===section));
    links.forEach(a=>{if(a.getAttribute('href')==='#'+section.id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    document.getElementById('current').textContent=section.dataset.title;
    const details=node?.closest('details');if(details)details.open=true;
    if(target && node && node!==section){setTimeout(()=>node.scrollIntoView({block:'start'}),10);}else{window.scrollTo(0,0);}
    document.getElementById('toc').classList.remove('open');document.getElementById('menu').setAttribute('aria-expanded','false');
  }
  window.addEventListener('hashchange',active);
  window.addEventListener('resize',sizeHeader);
  document.querySelectorAll('[data-check]').forEach(cb=>cb.addEventListener('change',()=>{state.done[cb.dataset.check]=cb.checked;persist();drawProgress();}));
  document.getElementById('reset').addEventListener('click',()=>{state.done={};drawProgress();persist();});
  document.getElementById('smaller').addEventListener('click',()=>{state.scale=Math.max(.85,+(state.scale-.05).toFixed(2));drawDisplay();persist();});
  document.getElementById('larger').addEventListener('click',()=>{state.scale=Math.min(1.4,+(state.scale+.05).toFixed(2));drawDisplay();persist();});
  document.getElementById('wrap').addEventListener('click',()=>{state.wrap=!state.wrap;drawDisplay();persist();});
  document.getElementById('focus').addEventListener('click',()=>{state.focus=!state.focus;drawDisplay();persist();});
  document.getElementById('menu').addEventListener('click',()=>{const nav=document.getElementById('toc');nav.classList.toggle('open');document.getElementById('menu').setAttribute('aria-expanded',String(nav.classList.contains('open')));});
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();document.getElementById('search').focus();}if(e.key==='Escape'){document.getElementById('toc').classList.remove('open');document.getElementById('menu').setAttribute('aria-expanded','false');}});
  function codeText(box){const spans=box.querySelectorAll('.line');return spans.length?[...spans].map(s=>s.textContent).join(''):box.querySelector('code').textContent;}
  document.querySelectorAll('.codebox .copy').forEach(button=>button.addEventListener('click',async()=>{
    const box=button.closest('.codebox'); const value=codeText(box);const fallback=box.querySelector('.copy-fallback');const textarea=fallback.querySelector('textarea');
    try {if(!navigator.clipboard||!navigator.clipboard.writeText)throw Error('clipboard not available');await navigator.clipboard.writeText(value);box.querySelector('.copy-status').textContent='コピーしました';}
    catch(e){fallback.hidden=false;textarea.value=value;textarea.focus();textarea.select();box.querySelector('.copy-status').textContent='手動で選択してコピーしてください';}
  }));
  const search=document.getElementById('search');const matches=document.getElementById('matches');const panel=document.getElementById('results');
  function find(){const query=search.value.trim().toLocaleLowerCase();matches.replaceChildren();
    if(query.length<2){panel.hidden=true;return;}
    const result=sections.filter(s=>s.textContent.toLocaleLowerCase().includes(query));panel.hidden=false;
    document.getElementById('search-count').textContent=result.length+'章が一致';
    result.forEach(s=>{const a=document.createElement('a');a.href='#'+s.id;a.textContent=s.dataset.title;matches.append(a);});
  }
  search.addEventListener('input',find);
  document.getElementById('clear-search').addEventListener('click',()=>{search.value='';find();});
  drawDisplay();drawProgress();active();
})();
</script>'''
    document = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="color-scheme" content="dark"><title>攻撃者視点のPythonペンテスト10作品 · 詳細開発マニュアル</title><style>' + css + '</style></head>'
                '<body><a class="skip" href="#main">本文へ移動</a><header><a href="#cover">PYTHON SECURITY · 10 LABS</a>'
                '<button class="js-only" id="menu" aria-controls="toc" aria-expanded="false">目次</button>'
                '<label class="search-label" for="search">全文検索 · Ctrl+K</label><input class="js-only" id="search" type="search" placeholder="本文・工程・完成ソース" aria-label="全文検索">'
                '<button class="js-only" id="smaller" aria-label="文字を小さく">A−</button><button class="js-only" id="larger" aria-label="文字を大きく">A＋</button>'
                '<button class="js-only" id="wrap" aria-pressed="false">折り返し</button><button class="js-only" id="focus" aria-pressed="false">集中表示</button>'
                '<div id="current" aria-live="polite">全20章を表示</div></header><div class="layout"><nav id="toc" aria-label="章の目次">' + nav +
                '<p id="progress">0 / 20章 完了</p><button class="js-only" id="reset">進捗チェックをリセット</button><p id="storage-status"></p></nav>'
                '<main id="main"><noscript><p class="note">JavaScriptが無効です。全章を続けて読めます。コピーと検索は手動で行ってください。</p></noscript>'
                '<div id="results" hidden><strong id="search-count" role="status"></strong><button id="clear-search">検索解除</button><div id="matches"></div></div>' + ''.join(parts) +
                '</main></div>' + js + '</body></html>')
    (ROOT/'Python_ペンテスト10作品_全行構文分解_20261111.html').write_text(document,encoding='utf-8')
    print('Manual written',len(document),'bytes',len(parts),'chapters')
    report = {'sum_minutes':sum(d['mins'] for d in DATA), 'project_count':len(DATA),'sections':len(parts), 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES},'sample_run': {f'{i:02d}':observed(d['cmd'])[0] for i,d in enumerate(DATA,1)}}
    (ROOT/'verification'/'manual_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':make()
