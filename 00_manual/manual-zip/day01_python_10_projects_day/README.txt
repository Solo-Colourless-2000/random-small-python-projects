Pythonミニプロジェクト10個 · 初学者向け 詳細開発マニュアル【精査改訂版】
====================================================================

■ 最初に開くもの
  ZIPを展開し、python_10_projects_day/manual.html をブラウザーで開きます。
  以前の教材に重ねず、空の別フォルダーへ展開してください。

■ 読む・作る順番
  1. 「本書の構成と使い方」と「環境構築」を読む。
  2. Python 3.10以上を確認し、教材フォルダーへ移動する。
  3. 「Pythonの基礎を具体例で学ぶ」を読み、短い例を別ファイルで試す。
  4. 各作品の工程を順番に、同じ practice/*.py へ一度だけ入力する。
  5. 完成コードと照合して保存し、章末のコマンドで結果を確かめる。
  6. 分からない行は付録Aの逐行解説で確認する。

  完成コードは照合用です。工程で書いたコードの末尾へ重ねて貼りません。
  途中の工程は構文が未完成の場合があります。全工程の後で実行します。
  「1日」はコース名・目安です。初学者は複数日に分けて進めて構いません。

■ 動作環境
  Linux、Python 3.10以上。プログラムとテストは標準ライブラリのみです。
  英語化後の実行確認はLinux / Python 3.13.5で行いました。
  Python全バージョン・全Linux環境での実機確認ではありません。
  Pythonの新規導入、OSパッケージ更新、公式資料の閲覧には通常ネット接続が必要です。
  準備後のマニュアル閲覧・10作品の実行にはネット接続は不要です。
  編集にはvimまたはnvimを使用します。UTF-8形式でファイルを保存してください。
  Windows・macOS向けの操作手順やPOSIX権限の互換性は対象にしていません。

■ ファイル
  manual.html         ダークテーマのマニュアル。全20セクション、41工程。
  projects/           10本の完成Pythonプログラム。答え合わせ用。
  samples/            練習用データ。report.pdfは拡張子集計用のダミー。
  tests/              59件の自動テスト（元の45件＋今回の回帰テスト14件）。
  README.txt          この案内。
  CHANGELOG.txt       主な修正と追加解説の一覧。
  TRANSLATION_REVIEW_2_PASSES.txt   英語化後の2周点検記録。
  REVIEW_REPORT.txt   24巡の観点別点検記録と検証範囲。
  verification/       今回の静的・実行点検記録。previous_revision/ は前回版の履歴。

■ まず動かす
  展開した python_10_projects_day/ の直下で実行します。

  python3 --version
  python3 projects/01_file_counter.py samples/downloads

  Total files: 4 と表示されれば、最初の実行を確認できています。
  projects/ は完成版、practice/ は自分で書く実習先です。
  samples/ などの相対パスは、実行時の現在地（pwd）からたどります。

■ 完成版10作品の実行例
  python3 projects/01_file_counter.py samples/downloads
  python3 projects/02_log_finder.py samples/logs/sample.log ERROR
  python3 projects/03_password_gen.py 16
  python3 projects/04_hash_file.py samples/downloads/readme.txt
  python3 projects/05_permission_check.py samples/downloads/readme.txt
  python3 projects/06_ip_checker.py 192.168.1.20 192.168.1.0/24
  python3 projects/07_url_analyzer.py "https://example.com:8443/login?id=10"
  python3 projects/08_csv_analyzer.py samples/csv/events.csv
  mkdir -p practice
  python3 projects/09_system_info.py practice/system_info.json
  python3 projects/10_directory_backup.py samples/documents practice/documents_backup.zip

  第9・10作品は既存出力を上書きしません。
  2回目は、まだ使っていない出力名へ変えてください。
  マニュアルの「画面に出る結果」は、初回実行の結果を照合する欄です。

■ 自動テスト
  python3 -m unittest discover -s tests -v

  今回の検証結果：全59件中57件成功、失敗0、2件スキップ（root環境 / Python 3.13.5）。
  tests/ は同梱 projects/ を対象とします。手入力した practice/ は各章で確認します。
  rootで実行した場合など、一部の権限テストがスキップされる場合があります。
  OKは検査した条件を満たす意味で、すべての障害を網羅する保証ではありません。

■ マニュアルの操作
  目次、Ctrl+K検索、文字サイズ、コード折返し、コピー、章末チェックを利用できます。
  チェックと設定の保存はブラウザーがローカル保存を許可する場合に利用できます。
  JavaScriptを無効にしても本文の全章を読めます。
  コピーが使えない場合はコードを選択してコピーします。説明用行番号は入力しません。

■ 作品の範囲
  ・パスワードは画面に表示されます。実際の秘密情報を共有しないでください。
  ・権限の変更実験は、自分で用意した練習ファイルだけで行います。
  ・IP所属判定とURL分解は、外部の機器やサイトに接続しません。
  ・URL分解の成功はURLの安全性や到達性の証明ではありません。
  ・CSVはeventの集計です。日時の正しさや全破損形式を検査するものではありません。
  ・ZIPは暗号化されません。元の所有者・ACL・日時の完全保存は行いません。
  ・ZIP範囲外の更新日時は1980〜2107年の範囲へ補正します。
  ・ZIP作成に失敗した場合、途中のZIPが残ることがあります。
  ・学習用の小さなツールです。実運用で必要な要件は別途検討します。
