Python Day02 · 10 Mini Projects / 精読レビュー・構文解説再修正版
改訂日：2026-11-11 / 元教材：2026-11-07
==============================================================

■ 開始方法
ZIPを展開し、manual.html をブラウザーで開いてください。
各作品の「4工程」を上から順に1ファイルへ追記し、完成後に
projects/ 内の参照ソースと diff -u で比較します。
完成コードを直接編集せず、practice/ へ自分で入力してください。

■ 今回の修正の中心（前回版から追加）
・コード行の構文説明に残っていた誤りを訂正しました。
  例：timedelta(minutes=25) の = は「代入」ではなく
      関数に名前付きで値を渡すキーワード引数の書式です。
  例：enumerate(CARDS, start=1) の丸括弧は関数呼び出し、
      (question, answer) はアンパックです。
  例：textwrap.fill(..., width=width) や output.open(...,
      encoding="utf-8") の = も同様です。
・f文字列の { }、リストの [ ]、条件式の if/else なども、
  コードの当該行の文脈に応じて説明を修正しました。
・10作品すべてに5段階の具体値追跡と、誤解しがちな点、
  自分で値を変えて確かめる練習を追加しました。
・英単語クイズの日本語訳を英語の実際のヒントに合わせました。
・完成コードは元の10作品を維持し、変更していません。

■ 確認結果
・32回の横断検証 × 10作品 = 320件の実行シナリオが成功。
  32回で入力値を変え、本文・付録の行を毎回照合。
  再現記録：verification/full_32_round_review.json
・元からある40観点の監査：40項目成功。
  検証結果：verification/audit_40_checks.json
・従来のunittest合計85件：73件と12件に分割して全件成功。
  一括実行が実行時間の上限に達したため、73件を25/25/23件に
  分けて実行し、残り12件を別に実行しました。
  記録：verification/unittest_chunk_0.log〜_2.log、
        verification/unittest_revision_12.log
・ブラウザー：Chromium 1440px / 390px / 320pxで横はみ出し
  なし、JavaScriptエラーなし。目次・検索・解説の展開と、
  JavaScript無効時の全章閲覧を確認。

■ 参考になる起動コマンド
python3 --version
python3 projects/02_bill_splitter.py 1000 3
python3 projects/05_study_planner.py 23:50 2
python3 projects/06_flashcard_quiz.py
python3 projects/10_svg_tiles.py practice/tiles.svg

■ 標準ライブラリのみの検証
python3 -m unittest discover -s tests -v
python3 verification/audit_40_checks.py

■ 補助的な32回の横断レビュー再実行（任意）
python3 verification/full_32_round_review.py
このスクリプトのみBeautiful Soup 4（bs4）が必要です。
10作品を作る・使う・単体テストするためには不要です。

■ ZIP内の構成
manual.html      20章、10作品、40工程、逐行解説と具体値トレース
projects/        完成済みPythonファイル10本（ASCII/英語）
practice/        自分で入力・保存する場所
samples/         入力例と照合用SVG
./tests/         既存テスト、85件
verification/    32回横断レビュー・40観点監査・ログ・画面写真
CHANGELOG.txt    変更履歴
REVIEW_REPORT.txt 独立した精読結果と残る制約
PROJECT_HISTORY.json 添付元ZIP由来の題材履歴（変更なし）

■ 重要な制約
動作確認はLinux / Python環境とChromiumで実施しました。
実際の学習時間やすべてのOS・ブラウザーでの動作を保証しません。
検証は添付された前回のDay02改訂版ZIPのみを基準にしています。
他の日の教材やLibraryの古いファイルを本文の正解データに使っていません。
