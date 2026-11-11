# Pythonペネトレーションテスト10作品：追加36観点の再監査・初学者向け強化版

更新日：2026-11-11。改訂元は**今回指定された32周点検版ZIP**（`Python_Offensive_Pentest_10Labs_20261111_32pass_annotated.zip`）だけです。別チャットのファイルやLibraryの過去成果物を補完ソースとして利用していません。

## 使い方（Linux、vim / Neovim）

1. `Python_Offensive_Pentest_10Labs_20261111_36additional_checks_refined.zip` を `~/Downloads/` に保存します。
2. 端末で以下を入力します。

```bash
cd ~/Downloads
python3 -m zipfile -e Python_Offensive_Pentest_10Labs_20261111_36additional_checks_refined.zip .
cd Offensive_Python_10Labs_Review68_20261111
python3 --version
ls
```

Python 3.10以降を想定。作品とHTML閲覧には追加Pythonパッケージは不要です。HTML `Python_ペンテスト10作品_全行構文分解_20261111.html` はローカルブラウザーで開き、目次から10作品を選んでください。各作品のSTEP 01〜04のコードは、`practice/` に自分で入力して完成させます。

```bash
mkdir -p practice
vim practice/01_header_audit.py
# STEP 01〜04を順に入力して保存
python3 practice/01_header_audit.py samples/response_headers.txt https
diff -u projects/01_header_audit.py practice/01_header_audit.py
```

`vim` では `i` で入力開始、`Esc` → `:wq` → Enter で保存して終了します。コードの字下げはスペース4個ずつです。STEPの途中は未完成です。STEP 04まで入力してから実行してください。

## 内容・改善点

- オフラインのHTTPヘッダー、Cookie、TCPループバック、パス検査、SQLite、認証試行のシミュレーション、HMAC、IDOR、PCAP、HTTP/1.1フレーミングの計10演習。
- コード非空行の逐行解説と、実際のPythonトークン（名前・演算子・数値・文字列・字下げ）の説明を維持。重要な30行を抽出し、各行の4つの構成要素、合計120箇所を新しく詳解。
- 04、05、06、08のPython関数を外部から直接呼び出した場合も、未知の動作モードを拒否。スペルミスなどで危険・無制限モードを選ぶ不具合を抑制。
- 07の署名検証では、ユーザー名とロールの基本的な型・長さも検査。ただし公開教材鍵で正しいMACを付け直せるため、`admin` の「正しい署名」が付いていても実際のアクセス認可は証明されません。
- 05〜08等のSTEP分割位置を再調整し、関数の実装段階と見出しを一致させました。
- ブラウザーの保存設定が壊れた場合にも、画面上の保存済み設定の型を確認してから利用するように改善。

## 自動テスト（用途に応じて実行）

```bash
python3 tests/run_groups.py 1
python3 tests/run_groups.py 2
python3 tests/run_groups.py 3
python3 tests/run_groups.py 4
python3 tests/test_revision.py
python3 verification/verify_manual.py
python3 verification/verify_examples.py 1
python3 verification/verify_examples.py 2
python3 verification/verify_examples.py 3
python3 verification/verify_examples.py 4
python3 verification/audit_30_checks.py
python3 verification/audit_24_new.py
python3 verification/audit_32_additional_rounds.py
python3 verification/audit_36_more_rounds.py
```

古い99件の回帰テストと、新しい10件の境界条件テストを別々に実行できます。HTMLとコードの一致検査は `verification/verify_manual.py`、例の出力は `verification/verify_examples.py` です。

追加36周は**毎回、監査記録自身とハッシュ一覧などの自己参照ファイルを除いた教材ファイルを開き直し、異なる焦点で検査した36回の決定的な自動点検**です。36人の監査人がそれぞれ実施した検証ではなく、全入力への安全性の証明でもありません。観点一覧と回数は `verification/36_MORE_ROUNDS.json` に記録します。従来の監査スクリプトも同梱します。

ブラウザー操作検証はPlaywright・Chromiumを別途用意した場合のみ、次で再現できます。これらは教材の実習そのものには不要です。

```bash
python3 verification/check_browser.py
python3 verification/layout_checks.py small
python3 verification/layout_checks.py large
```

## 安全上の前提と学習上の制限

すべて同梱の合成データ、メモリDB、または127.0.0.1のデモです。無断で第三者のサイトを走査・認証試行するための教材ではありません。05の危険なSQL文字列連結は学習専用です。04のパス検査はTOCTOU競合を防ぐ完全な機能ではありません。06は仮想の共通試行上限で、実際の認証のレート制御とは異なります。07の`verify`はMAC・基本構造の点検であり、認可の実装ではありません。09のPCAP、10のHTTPは部分パーサーであり、PASS・VALID等の表示は本番システムの安全性を保証しません。

## 同梱の根拠・記録

- `projects/`: 10作品の完成Pythonソース。
- `samples/`: すべて架空の教材データ。
- `tests/`: 既存99テストと今回追加した10テスト。
- `verification/critical_line_walkthroughs.json`: 重点30行の分解説明と注意点。
- `verification/REVIEW_REPORT.txt`: 今回の修正と実測検証結果。
- `verification/36_MORE_ROUNDS.json`: 新たな36種類の自動監査記録。
- `verification/REFERENCES.md`: Python公式文書など、追加学習の参照先。
- `verification/FILE_HASHES.sha256`: 配布物のファイルハッシュ。

技術的な豆知識として、`hmac.compare_digest` のような「比較時の情報漏えいに配慮したAPI」を選ぶことと、「何を許可するか」という認可の判断は、セキュリティ設計でまったく異なる役割です。実際のシステムでもこの2つを混同しないことが大切です。
