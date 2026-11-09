Pythonミニプロジェクト10個 · 第2集【精査改訂版】
暮らし・学習・小さな遊び ／ 2026-11-07
============================================================

■ 最初に開くもの
  ZIPを展開し、python_10_projects_day02_20261107_refined/manual.html を
  ブラウザーで開いてください。以前の教材と別のフォルダーで使います。

■ 今回の条件
  日本語の詳しいマニュアル。コード内は英語のみです。
  docstring、入力案内、画面表示、エラーにも日本語を含めていません。
  エディターはvimを使用します。
  基本実習は合計220分、準備・休憩・確認を含め約5〜6時間が目安です。
  4工程を入力し、基本例の結果を照合すれば各作品は完成です。
  逐行解説の全読や追加問題は任意の復習です。

■ 環境
  Linuxの操作手順、Python 3.10以上、標準ライブラリのみ。
  実機検証：Linux / Python 3.12.14。
  Pythonとvimの準備後は、本文の閲覧と作品の実行はオフラインでできます。

■ まず試す（教材フォルダー内で実行）
  python3 --version
  python3 projects/02_bill_splitter.py 1000 3

  People paying 334 JPY: 1
  People paying 333 JPY: 2
  Checked total: 1000 JPY

■ 自分で入力する
  mkdir -p practice
  vim practice/01_temperature.py

  vimが開いたら i で挿入モードへ入ります。
  工程1〜4を同じファイルへ順番に追記します。
  全工程の後、Esc → :wq → Enter で保存して終了します。
  入力例の行番号は入力しません。
  完成コードを末尾へ重ねて貼りません。

■ 完成版10作品の実行例
  python3 projects/01_temperature.py
    → 実行後に18を入力
  python3 projects/02_bill_splitter.py 1000 3
  python3 projects/03_recipe_scaler.py 3
  python3 projects/04_date_countdown.py 2026-11-07 2026-11-10
  python3 projects/05_study_planner.py 09:00 2
  python3 projects/06_flashcard_quiz.py
    → apple、pen、waterを順に入力
  python3 projects/07_text_wrapper.py 12 "Python makes small tools easy to build."
  python3 projects/08_score_bars.py 60 85 100
  python3 projects/09_treasure_hunt.py
    → 1 1、4 2を順に入力
  python3 projects/10_svg_tiles.py practice/tiles.svg
    → 作成したSVGをブラウザーで開く

  第10作品は同名ファイルを上書きしません。
  再実行するときはpractice/tiles_2.svgなど新しい名前に変えます。

■ ファイル
  manual.html             20セクション、40工程のマニュアル
  projects/               完成Pythonコード10本（全ファイルASCII）
  practice/               自分の実習先
  samples/                対話入力のサンプル、完成イメージのSVG
  tests/                  標準ライブラリで動く自動テスト
  verification/           テスト結果、HTML整合性、ブラウザー確認、画像
  PROJECT_HISTORY.json    添付の既出10題＋今回10題の題材台帳
  REVIEW_REPORT.txt       検証範囲と結果

■ 確認
  python3 -m unittest discover -s tests -v

  今回の結果：85件成功、失敗0、スキップ0。
  テストは同梱projects版が対象。手入力したpractice版は章末で照合します。
  教材のコード欄・完成ファイル・付録Aが一致することも確認しました。

■ 画面の機能
  章目次、全文検索、コードコピー、文字サイズ、コード折り返し、
  集中表示、章末チェック。JavaScript無効時も全20セクションを読めます。
  設定の保存はブラウザーがローカル保存を許可している場合に利用できます。

■ 題材の履歴
  添付ZIPと今回の目的・入力・出力・中心処理を台帳に記録しています。
  台帳を次の教材作成でも参照し、題名だけ変えた再利用を避けます。
  添付以外の過去資料は今回の確認範囲に含まれていません。

■ 精査改訂
  12巡の観点別点検を実施。全10作品に値の表と追加用語解説を増補。
  変更一覧はCHANGELOG.txt、各巡の記録はverification/audit_12_passes.json。
  増補解説の全読は基本実習220分とは別です。
