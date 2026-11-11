# 参考文献と一次資料の範囲

**今回の編集・検証で使用した唯一の一次資料**: 今回の改訂元として渡された `Python_Offensive_Pentest_10Labs_20261111_32pass_annotated.zip` の中のソース、HTML、テスト、サンプルおよび監査記録。過去の別チャットやLibraryの別ファイルを内容補完に使用していません。

Pythonの文法と標準ライブラリについて、さらに深く学ぶ際の二次参考資料（リンク先の内容をZIP外のデータ補完や実攻撃対象の選定に使用していません）:

- Python Tutorial: https://docs.python.org/3/tutorial/index.html
- Python Language Reference: https://docs.python.org/3/reference/index.html
- Python tokenizer: https://docs.python.org/3/library/tokenize.html
- pathlib: https://docs.python.org/3/library/pathlib.html
- socket: https://docs.python.org/3/library/socket.html
- sqlite3: https://docs.python.org/3/library/sqlite3.html
- hmac: https://docs.python.org/3/library/hmac.html
- struct: https://docs.python.org/3/library/struct.html
- json: https://docs.python.org/3/library/json.html

セキュリティとプロトコルの追加学習資料:

- OWASP HTTP Headers Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP SQL Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- RFC 6265 (Cookies): https://www.rfc-editor.org/rfc/rfc6265.html
- RFC 791 (IPv4): https://www.rfc-editor.org/rfc/rfc791.html
- RFC 9110 (HTTP Semantics): https://www.rfc-editor.org/rfc/rfc9110.html
- RFC 9112 (HTTP/1.1): https://www.rfc-editor.org/rfc/rfc9112.html

仕様書が対象とする一般的な実装と、本教材の簡易チェックが実装する部分集合は区別してください。HMACの有効な署名だけでは実サービスの認可は成立しません。また、「結果が表示された」ことは「脆弱性を安全に検査できた」こととは同義ではありません。
