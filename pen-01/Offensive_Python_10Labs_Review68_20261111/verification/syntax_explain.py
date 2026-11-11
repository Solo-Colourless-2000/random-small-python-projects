"""Produce concrete, per-physical-line Python token explanations from source.

This is a lexical teaching aid, NOT an interpreter or a security verifier.
All descriptions refer to the actual ten source files, never detached examples.
"""
from __future__ import annotations

import ast
import io
import keyword
import tokenize
from collections import defaultdict
from pathlib import Path

OPERATORS = {
    '=': '代入。右辺の値を左辺の名前へ結び付ける（比較には==を使用）',
    '==': '等しいか比較し、TrueまたはFalseを返す',
    '!=': '異なるか比較する',
    '<': '左辺が右辺より小さいか比較する',
    '>': '左辺が右辺より大きいか比較する',
    '<=': '以下か比較する',
    '>=': '以上か比較する',
    '+': '数値の加算、または同じ型同士の連結',
    '-': '数値の減算。単項なら負数を表す',
    '*': '数値の積、または列の反復。引数中では展開にも使う',
    '/': '割り算',
    '//': '小数部を切り下げる除算',
    '%': '剰余。文字列の書式化にも使われることがある',
    '&': '整数のビットごとのAND',
    '|': '整数のビットごとのOR',
    '>>': 'ビットを右へずらして値を読み取る',
    '<<': 'ビットを左へずらす',
    ':': '条件・関数・ループのブロック開始、または辞書のキーと値・スライスの区切り',
    ',': '引数・項目・代入対象を分ける',
    '.': '左側のオブジェクトの属性またはメソッドを参照する',
    '(': '引数や式を開始する括弧。文脈によりタプルにも使われる',
    ')': '対応する丸括弧を閉じる',
    '[': '添字・スライス参照、またはリストの要素を開始する',
    ']': '対応する角括弧を閉じる',
    '{': '辞書・集合などの要素を開始する。f文字列では埋め込みにも使う',
    '}': '対応する波括弧を閉じる',
    '->': '関数の返り値の型ヒントを示す',
    ':=': '式の中で値を変数へ代入する',
}
KEYWORDS = {
    'def': 'ここから関数を定義する。次の名前は関数名',
    'return': '関数の処理を終え、呼び出し元へ値を返す',
    'if': '直後の条件を評価して分岐を開始',
    'elif': '直前の条件が偽のとき次の条件を調べる',
    'else': 'それまでの条件に当てはまらないときの処理',
    'for': '要素を1個ずつ取り出す反復を開始',
    'in': 'コレクションの要素検査、またはforの繰り返し元を示す',
    'not': '直後の真偽値を反転する',
    'and': '両方真のとき真。左が偽なら右を評価しない',
    'or': 'どちらかが真なら真。左が真なら右を評価しない',
    'is': '値の等しさではなく同一オブジェクトかを検査',
    'with': 'コンテキスト管理を開始して終了時の後片付けを確実にする',
    'as': 'importの別名やwith/exceptの結果を名前に結び付ける',
    'try': '例外を捕捉する範囲を開始する',
    'except': '指定した例外が起きた場合の処理を開始',
    'raise': '例外を発生させて通常の流れを中断する',
    'import': 'モジュールや名前を読み込む',
    'from': '指定モジュール内の名前を読み込む開始句',
    'while': '条件が真の間、繰り返す',
    'continue': '現在の反復の残りを飛ばして次へ進む',
    'break': '現在のループを抜ける',
    'True': '真偽値の真',
    'False': '真偽値の偽',
    'None': '値がないことを示す特別なオブジェクト',
}
BUILTINS = {
    'len': '文字列・リスト・bytesなどの長さを返す組込み関数',
    'print': '文字列などを標準出力へ表示する組込み関数',
    'int': '整数型を示す、または値を整数へ変換する組込み関数',
    'str': '文字列型を示す、または文字列へ変換する組込み関数',
    'bytes': 'バイト列の型と変換関数',
    'range': '連続する整数の範囲を作る',
    'enumerate': '順番を示す整数と要素を同時に取り出す',
    'sorted': '並び替えた新しいリストを作る',
    'any': '1つでも真ならTrueを返す',
    'all': 'すべて真ならTrueを返す',
    'set': '重複のない集合を作る',
    'dict': 'キーと値の対応を作る',
    'isinstance': 'オブジェクトの型を検査する',
    'ord': '1文字に対応する整数の文字コードを得る',
    'chr': '整数から対応する1文字を得る',
    'list': 'リストを作る',
    'tuple': 'タプルを作る',
    'ValueError': '値の形式が不正な場合に使う例外型',
    'OSError': 'OSやファイル・ソケット操作に関係する例外型',
    'UnicodeError': '文字エンコードやデコードに関する例外型',
    'SystemExit': '処理を終了ステータス付きで終了させる例外型',
    'TypeError': '型が操作に合わない場合の例外型',
}
NAMES = {
    'sys': '標準ライブラリ。コマンド引数を読む',
    'argv': 'コマンドライン引数のリスト。[0]はファイル名',
    'Path': 'pathlibのパスオブジェクトを作るクラス',
    '__file__': '実行中のソースファイルの場所を表す名前',
    '__name__': '直接実行なら__main__となるモジュール名',
    'socket': 'TCPソケット通信を扱うモジュール',
    'HOST': '接続先を127.0.0.1に固定した教材の定数',
    'ROOT': '公開領域に見立てたルートディレクトリ',
    'SAMPLES': '同梱サンプルの場所を表す定数',
    'LAB_KEY': '公開済み教材専用HMAC鍵。実運用禁止',
    'payload': 'トークンや要求に含まれるデータ本体',
    'fields': 'ヘッダー名から値一覧への辞書',
    'attrs': 'Cookie属性名と設定値を対応させる辞書',
    'notes': 'ヘッダー点検で見つかった注意事項の一覧',
    'warnings': 'Cookie検査の注意事項一覧',
    'lines': 'ファイル行や解析結果を並べたリスト',
    'port': 'TCPのポート番号（1～65535）',
    'server': '127.0.0.1で待ち受けるデモソケット',
    'client': '確立したTCP通信を扱うソケット',
    'db': 'メモリ内のSQLite接続',
    'query': '実行するSQL文、または検索文字列',
    'rows': 'SQLの検索結果の行一覧',
    'source': '送信元、または読み込み対象データ',
    'target': '対象ファイル、もしくは要求ターゲット',
    'base': 'パスの基準となる実在ディレクトリ',
    'decoded': 'エンコードから復元したデータ。04ではURL文字列、07ではBase64URLのバイト列',
    'frame': 'Ethernetフレームのバイト列',
    'ip': 'IPv4部分のバイト列',
    'header_length': 'IPv4のヘッダー長（バイト数）',
    'packet_length': 'IPv4の全長フィールド値（バイト数）',
    'offset': '次に読む位置を示すバイトオフセット',
    'snaplen': 'PCAP保存時の最大キャプチャ長',
    'caplen': 'PCAPに保存された実際のレコード長',
    'original': '元のパケットの長さ',
    'transport': 'TCPまたはUDP部分のバイト列',
    'data': '読み取ったファイルの内容（strかbytesは文脈次第）',
    'token': 'ドット区切りの教材用署名付きトークン',
    'signature_part': 'トークンの署名部分',
    'payload_part': 'トークンの本文部分',
    'role': '認可の判断に使う利用者の役割',
    'actor': '操作を要求する架空の利用者',
    'document': 'アクセス先の架空文書',
    'action': 'readまたはeditという操作',
    'mode': 'unsafeとsafeなど比較する動作モード',
    'body': 'HTTPヘッダーのあとに続く本文のバイト列',
    'lengths': 'Content-Lengthヘッダーの値の一覧',
    'transfers': 'Transfer-Encodingヘッダーの値の一覧',
}


METHODS = {
    'split': '指定した区切り文字で文字列・bytesを複数部分へ分ける',
    'splitlines': '改行位置で分割する（本教材のヘッダー入力では使わない）',
    'strip': '先頭と末尾の空白などを取り除く。元の値は変更しない',
    'lstrip': '先頭側だけ文字や空白を取り除く',
    'rstrip': '末尾側だけ指定した文字や空白を取り除く',
    'lower': 'アルファベットの大文字を小文字へ変換して比較しやすくする',
    'startswith': '指定した文字列で始まるかを真偽値で返す',
    'endswith': '指定した文字列で終わるかを真偽値で返す',
    'replace': '指定部分を別の文字列に置き換えた新しい値を返す',
    'append': 'リストの末尾に1個の要素を追加する',
    'get': '辞書のキーに対応する値を取り出す。なければ既定値を返す',
    'setdefault': '辞書にキーがなければ初期値を登録し、その値を返す',
    'items': '辞書のキーと値を組として順に取り出す',
    'partition': '最初に現れた区切り文字で前・区切り・後ろの3要素に分ける',
    'count': '対象文字列や要素が何回現れるかを数える',
    'join': '並びの文字列を指定した区切り文字で連結する',
    'read_bytes': 'ファイルをバイト列として読む。文字コード変換はしない',
    'read_text': '指定した文字コードでファイルを文字列として読む',
    'stat': 'ファイルサイズなどの情報を取得する',
    'resolve': 'パスを解決し、シンボリックリンクなどを反映した実体パスを得る',
    'is_relative_to': 'あるパスが指定された基準ディレクトリの内側かを判定する',
    'is_absolute': '絶対パスかどうかを判定する',
    'is_file': '通常ファイルかを調べる',
    'is_ascii': 'ASCIIだけで構成されるかを調べる',
    'isascii': 'すべての文字がASCII範囲に収まるか判定する',
    'isdecimal': '文字が十進数字だけで構成されるかを確認する',
    'isdigit': '数字文字だけかを検査する。ASCII限定には別の検査も必要',
    'isalnum': '英字または数字の文字だけかを調べる',
    'isspace': '空白文字かを調べる',
    'fullmatch': '入力全体が正規表現に一致するか検査する',
    'decode': 'bytesを指定文字コードでstrへ変換する（別名の教材関数decodeとは文脈で区別）',
    'encode': 'strを指定文字コードのbytesへ変換する（教材関数encodeとは文脈で区別）',
    'dumps': 'Pythonの辞書などをJSON形式の文字列に変換する',
    'loads': 'JSON形式の文字列をPythonの値に戻す',
    'urlsafe_b64encode': 'バイト列をURL安全なBase64形式へ変換する',
    'b64decode': 'Base64形式のバイト列を復元する',
    'compare_digest': '比較時の情報漏えいを抑えるために使う比較関数',
    'new': 'HMACなどの新しいオブジェクトを作る',
    'sha256': 'SHA-256のハッシュアルゴリズムを指定する',
    'digest': '計算済みのHMACなどをbytesとして取り出す',
    'execute': 'SQLiteのSQL文を実行する。?に値を渡す形が安全な結合方式',
    'executemany': 'SQL文を複数のパラメーター組について実行する',
    'fetchall': 'SQLクエリーの結果行をすべて取り出す',
    'connect': 'SQLiteデータベースへの接続を作る',
    'create_connection': '指定先にTCP接続を試みる',
    'settimeout': 'ソケットの待ち時間の上限を設定する',
    'recv': '受信データを最大指定バイト数だけ取り出す',
    'bind': 'ソケットが待ち受けるIPとポートを指定する',
    'listen': 'TCPの接続要求を待てる状態にする',
    'accept': '来た接続を1つ取り出す。新しい通信用ソケットを返す',
    'sendall': '指定したバイト列をすべて送るよう試みる',
    'getsockname': '自身のソケットに割り当てられたIP・ポートを調べる',
    'start': 'スレッドの処理を開始する',
    'Thread': '並行して関数を実行するスレッドを作る',
    'from_bytes': '複数バイトの整数を指定したバイト順に従って読む',
    'unpack': '固定長のバイト列から構造化した値を取り出す',
    'unpack_from': '指定したオフセットから構造化したバイト列を読み取る',
    'IPv4Address': '4バイトのIPv4アドレスを表示しやすいオブジェクトへ変換',
}

VARIABLES = {
    'value':'解析や比較の対象となる値', 'name':'対象のヘッダー名・Cookie名・利用者名など',
    'exc':'exceptで受け取った例外オブジェクト。発生理由を表示する',
    'line':'ファイルから取り出した1行の文字列・bytes',
    'ch':'調べている文字を1個ずつ受け取る変数',
    'user':'架空アカウントの名前', 'args':'コマンドライン引数を入れた配列',
    'raw':'変換前の生データ', 'path':'入力として指定されたファイルパス',
    'banner':'TCP接続先から返された表示用バイト列を解釈した文字列',
    'key':'辞書・属性の識別用の名前', 'status':'TCP接続の成否を表す状態',
    'request_parts':'HTTPリクエスト行を空白で3つに分けた部分',
    'attempts':'架空のパスワード試行の累計回数',
    'protocol':'IPv4の上位プロトコル番号。6=TCP、17=UDP',
    'part':'分割した文字列の1項目', 'flag':'SecureやHttpOnlyなどの属性名',
    'message':'署名対象の文字列、または表示する通知',
    'successes':'一致した架空アカウントを記録するリスト',
    'order':'PCAPの数値を読むときのバイト順を指定する文字',
    'parts':'区切り文字で分割した項目一覧', 'secure_present':'Secure属性が存在するかを示す真偽値',
    'same_site':'CookieのSameSite属性の値', 'setting':'Cookie属性で=の後に指定された値',
    'match':'試行したパスワードが一致したかの真偽値',
    'prefix':'文字列が始まるべき接頭辞', 'line_number':'保存データの何行目かを示す連番',
    'scheme':'入力元をHTTPまたはHTTPSとして解釈する設定',
    'values':'同名HTTPヘッダーで得た複数の値のリスト',
    'csp':'Content-Security-Policyの値一覧', 'referrer':'Referrer-Policyの値一覧',
    'sts':'Strict-Transport-Securityの値一覧',
    'reply':'ソケットで受信した最大64バイトの内容',
    'thread':'デモサーバーの受け付け処理を実行するスレッド',
    'encoded':'Base64URLで表現したテキスト',
    'changed':'改ざん後の教材トークン本文', 'result':'検査や関数から得られた結果',
    'results':'検索に一致した値の一覧', 'header_bytes':'HTTP要求のヘッダー部分のbytes',
    'tcp_header':'TCPヘッダー長のフィールドから計算したバイト数',
    'udp_length':'UDPのlengthフィールド値', 'magic':'PCAPの形式とバイト順を示す先頭4バイト',
    'micros':'タイムスタンプのマイクロ秒部分',
    'index':'順番を示す番号', 'row':'SQL結果の1行', 'source':'送信元アドレス等',
    'dest':'宛先ポート番号', 'address_a':'送信元IPv4アドレス',
    'address_b':'宛先IPv4アドレス', 'network':'PCAPに記録されるリンク層の種類',
    'major':'PCAP形式のメジャーバージョン', 'minor':'PCAP形式のマイナーバージョン',
    'transport_min':'TCP/UDPの最小ヘッダー長',
    'original':'もとのパケット長', 'kind':'TCPまたはUDPの表示用文字列',
}


def _number_description(value):
    if value.lower().startswith('0x'):
        return '16進数で書かれた整数（0xは16進数を示す）'
    if '_' in value:
        return '数字の区切りに_を使った数値（_は値に影響しない）'
    return '数値リテラル。strではなく計算できる値'


def _string_description(value):
    prefix = value.split('"', 1)[0].split("'", 1)[0].lower()
    if 'b' in prefix:
        return 'bytes型の定数。HTTPやPCAPの生のバイトと比較する'
    if 'f' in prefix:
        return 'f文字列。{式}の計算結果を文字列へ埋め込む'
    if 'r' in prefix:
        return 'raw文字列。\\を通常のエスケープとして扱わない（正規表現向き）'
    if value.startswith(('"""', "'''")):
        return '三重引用符の説明文（docstring）'
    return 'str型の文字列定数。引数や表示・比較に使う'


def tokenize_source(source: str):
    result = defaultdict(list)
    defined_functions = {node.name: node.lineno for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for tk in tokenize.generate_tokens(io.StringIO(source).readline):
        ln = tk.start[0]
        typ, token = tk.type, tk.string
        if typ in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE,
                   tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
            continue
        if typ == tokenize.COMMENT:
            result[ln].append(('#', 'この行の残りはコメントで、プログラム実行には使われない'))
        elif typ == tokenize.NAME:
            if token in KEYWORDS:
                desc = KEYWORDS[token]
            elif token in BUILTINS:
                desc = BUILTINS[token]
            elif result[ln] and result[ln][-1][0] == '.' and token in METHODS:
                # Same method name can mean unrelated operations by receiver type.
                # In these ten scripts, thread.join waits, while str.join combines text.
                if token == 'join' and len(result[ln]) >= 2 and result[ln][-2][0] == 'thread':
                    desc = 'thread.join(): デモ用スレッドの終了を待つ。timeoutは待機時間の上限（秒）'
                elif token == 'isdigit' and len(result[ln]) >= 2 and result[ln][-2][0] == 'value':
                    desc = 'valueがbytesなので、0～9のASCII数字だけか判定する（str.isdigitとは範囲が異なる）'
                else:
                    desc = METHODS[token]
            elif token in NAMES:
                desc = NAMES[token]
            elif token in VARIABLES:
                desc = VARIABLES[token]
            elif token in defined_functions:
                desc = f'このファイルの{defined_functions[token]}行で定義された関数。呼び出すと本体を実行する'
            elif keyword.iskeyword(token):
                desc = 'Pythonが定義する予約語'
            elif token.isupper():
                desc = '定数として扱う名前（Pythonの文法上は変更可能）'
            else:
                desc = 'この処理で使う変数・関数・属性などの名前。役割は左の説明と対応する'
            result[ln].append((token, desc))
        elif typ == tokenize.NUMBER:
            result[ln].append((token, _number_description(token)))
        elif typ == tokenize.STRING:
            short = token if len(token) <= 32 else token[:29] + '...'
            result[ln].append((short, _string_description(token)))
        elif tokenize.tok_name.get(typ, '').startswith('FSTRING_'):
            descriptions = {'FSTRING_START': 'f文字列の開始。中の{式}は評価される', 'FSTRING_MIDDLE': 'f文字列の通常の文字部分（式以外）', 'FSTRING_END': 'f文字列の終了'}
            result[ln].append((token[:29] if token else '(空)', descriptions[tokenize.tok_name[typ]]))
        elif typ == tokenize.OP:
            result[ln].append((token, OPERATORS.get(token, 'この式を区切る記号・演算子')))
        elif typ == tokenize.ERRORTOKEN and token.strip():
            result[ln].append((token, '字句解析で個別の記号として現れた文字'))
    return result


def explain_line(line: str, tokens):
    if not line.strip():
        return ''
    segments = []
    indent = len(line) - len(line.lstrip(' '))
    if indent:
        segments.append(('先頭の空白' + str(indent) + '個', '4スペースずつ深くなると、その内側の処理ブロックを表す'))
    # Every distinct occurrence is retained, including repeated operators.
    segments.extend(tokens)
    return ' ／ '.join(f'{label}：{description}' for label, description in segments)
