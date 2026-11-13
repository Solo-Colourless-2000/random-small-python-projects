# Python GUIセキュリティ実践7作品：全行・全構文要素解説マニュアル v7

## 最初に開くファイル

**`Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html`** をブラウザーで開く。日本語、ダークモード固定、オフライン動作のHTML。第4章からPythonの用語、各プロジェクト章から実際のコードとGUIを学べる。

このZIPは、**直前に作成されたv6 ZIP** `Python_GUI_セキュリティ実践7作品_全行詳細解説_36観点監査_20261111.zip` を唯一の修正元として作成した。Library内の別資料や別チャットの成果物から、内容や正解データを継ぎ足していない。v6が持つさらに古い監査記録は履歴として残している。

## この版で重点的に直したこと

- **7本のPython完成ソース（合計785物理行）の、空行を除く696行**すべてにある「行ごとの解説」を維持。
- v6の構成要素表では、同じ記号が1行に複数回現れると2回目以降の説明を省く場合があった。今回、Pythonの`tokenize`が返す**6,504個の字句要素を、出現順・重複も含めて**解説表に掲載し直した。
- `def`内の`=`、関数呼び出し時の`=`、通常の代入の`=`を区別。`raise ... from ...`、`except ... as ...`、`with ... as ...`、`set()`と`.set()`、集合の`|`とビット演算の`|`などの説明を改めた。
- `reader`、`item`、`row`、`command`、`padx`、`textvariable`など、約1,000箇所の曖昧だった名前の説明を具体化。
- 7作品それぞれに**6つずつ、合計42の手作業で選んだ精読事例**を追加。コードの位置、構文、値の移動、検証した出力、セキュリティ上の限界を1つの表で確認できる。
- 初学者用の第4章に「同じ記号でも意味が変わる」対照表を追加。
- 既存の17章、28 STEP、全完成コード、サンプル、元のGUI操作、ダークモード、検索、目次、折りたたみは維持。

**7本の完成Pythonソースはv6から1バイトも変更していない。** 動作するコードを無理に書き換えるのではなく、誤解を招く説明と教材としての整合性を重点的に修正した。

## 収録した7作品

| No. | 作品 | 学習の中心 |
|---|---|---|
| 01 | 認証ログの調査ボード | CSV、辞書、FAIL件数、検索と集計対象の違い |
| 02 | HTTPヘッダー監査デスク | 同名ヘッダー、CSP、HSTS、Cookieの簡易検査 |
| 03 | ファイアウォールルール可視化 | CIDR、ポート、ルールと実際の通信可否の違い |
| 04 | IOC照合コンソール | 正規化、集合、完全一致と侵害の証明の違い |
| 05 | ファイル改変検知ボード | SHA-256、ディレクトリ走査、スナップショットの限界 |
| 06 | メールヘッダーの手がかり抽出 | From/Reply-To、メール構文、認証結果の真正性 |
| 07 | ログイン試行制限シミュレーター | クラス、状態管理、時間窓、ロック期限 |

標準学習ルートは680分（11時間20分）。42の新しい精読事例や全6,504要素の説明を逐一読む場合、これより時間がかかる。

## 動作環境と起動

Linuxデスクトップ + Python 3.10以上 + Tkinter。教材で使うPython追加ライブラリは不要。ZIPを展開したフォルダの直下で実行する。

```sh
python3 -m tkinter
python3 projects/01_auth_log_board.py
python3 projects/02_http_header_audit.py
python3 projects/03_firewall_rule_viewer.py
python3 projects/04_ioc_match_console.py
python3 projects/05_integrity_baseline.py
python3 projects/06_email_header_clues.py
python3 projects/07_login_throttle_lab.py
```

作例を自分で書く場合は `practice/` に保存し、元の完成コードとサンプルは変更しない。ファイル改変検知の演習では `samples/integrity_folder/` を別の作業用フォルダにコピーして使用する。

## 検証方法

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
python3 tests/review_35_independent_cases_v5.py
python3 tests/review_35_semantic_rounds.py
python3 tests/review_36_passes.py
python3 tests/review_28_additional_passes.py
```

GUI用テストはLinuxの仮想ディスプレイ環境で実行可能。

```sh
xvfb-run -a python3 tests/gui_smoke.py
xvfb-run -a python3 tests/gui_interaction_smoke.py
```

`tests/test_v7_42_case_reading.py` は作品ごとの限界・境界値・表示内容など42件を検証する。`tests/test_v7_token_integrity.py` は696行・6,504要素の完全な出現順一致などを確認する。従来の142件と合わせ、v7のunittest総数は **187件**。

新規の42件、旧版の36・35・28観点のチェックは、異なる観点からの自動検査と重要箇所の実コード精読であり、**マニュアル全体を人間が30回以上逐語的に読み直したという意味ではない**。実行結果と検査上の限界は `REVIEW_REPORT_V7.md` に記載。

## セキュリティの重要な注意

7作品はすべて**ローカル・オフラインの学習用モデル**。HTTPヘッダー検査はブラウザーによるセキュリティ適用を証明しない。ファイアウォールのルール判定は実際の到達性を保証しない。IOC完全一致は侵害の確定ではない。ファイルハッシュの一致は原子的なスナップショットを意味しない。メールヘッダーに認証結果が書かれていても真正性は未検証。ログイン制限は実アカウント・実通信を使わない模型。必ず架空の同梱サンプルで試す。

## ファイル一覧

- `Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html`：メイン教材
- `projects/`：完成Pythonソース7本
- `samples/`：架空の入力データ
- `images/`：元のGUI画面画像7枚
- `practice/`：練習用ディレクトリ
- `tests/`：原版テストおよびv7の新しい検査
- `PROJECT_HISTORY.json`：作品台帳・版情報
- `REVIEW_REPORT_V7.md`：今回の検証・修正・限界
- `V7_EDIT_STATS.json`、`V7_TOKEN_AUDIT.json`、`V7_NAME_ENRICHMENT.txt`：編集の内訳
- `CHECKSUMS.sha256`：配布内容のファイル整合性確認用
- その他の `REVIEW_*` / `EDITORIAL_*`：過去版からの監査履歴

## 参考・出典

内容の唯一の改訂元は、前回のv6 ZIP。その他の出典は改訂の正解データとして使っていない。HTML内の外部サイトは任意の発展学習先で、教材自体はオフラインで利用できる。
