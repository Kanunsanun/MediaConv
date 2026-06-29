# MediaConv

ローカルで動作する PDF・音声 変換デスクトップアプリ（PyQt5）。
PDF 系の変換はすべてオフライン、音声変換のみ ffmpeg を使用（配布版は同梱）。

## 起動

`MediaConv.bat` をダブルクリック。
（コンソールから起動する場合）

```
.venv\Scripts\python.exe app.py
```

## 機能

| メニュー | 内容 |
|---|---|
| PDF → 画像 | 各ページを PNG / JPG に書き出し（DPI・ページ指定可・複数枚は ZIP 出力） |
| 画像 → PDF | 複数画像を 1 つの PDF に結合（ドラッグで順番並べ替え可） |
| PDF → テキスト | 文字を抽出して .txt に保存 |
| PDF → Word | 編集可能な .docx に変換（レイアウト保持を試行） |
| 結合 | 複数 PDF を 1 つに連結（リストをドラッグして順番変更可） |
| 分割 | 1 ページずつ / N ページごと / 範囲指定で分割（複数は ZIP 出力） |
| 回転 | 指定ページを 90°/180°/270° 回転 |
| 圧縮 | 画像を再エンコードしてサイズ削減 |
| 音声変換 | 音声を WAV / MP3 / FLAC / AAC に変換（複数まとめて変換可） |

- ページ指定欄は `1-3,5,8-` のような書式（空欄=全ページ、1 始まり）。
- **入力欄・リストはドラッグ&ドロップ対応**（ファイルを放り込むだけで指定できます）。
- 「複数枚になる場合は ZIP にまとめる」はチェックで切替（PDF→画像 / 分割）。
- 配布用 `setup.exe` の作り方は [PACKAGING.md](PACKAGING.md) を参照。

## 音声変換について（ffmpeg を使用）

音声変換機能は **ffmpeg** を使用します。

- 開発時（スクリプト実行）: PATH に ffmpeg があれば自動検出
- 配布版（setup.exe）: インストーラに ffmpeg を同梱するため利用者の追加作業は不要

詳細は [PACKAGING.md](PACKAGING.md)。

## 依存ライブラリ

`requirements.txt` 参照。`.venv` に導入済み。再構築する場合:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- PyMuPDF … PDF↔画像 / テキスト / 結合分割回転 / 圧縮
- pdf2docx … PDF→Word
- 音声変換 … ffmpeg（外部・配布版は同梱）
- Pillow … 画像処理
