# 配布用パッケージング（setup.exe の作り方）

一般的な Windows PC で「Python もライブラリも無し」で動く `setup.exe` を作る。
外部バイナリは **ffmpeg のみ**（音声変換用）。OCR は廃止したため Tesseract は不要。

```
[ソース] app.py / pdf_ops.py
   │  PyInstaller
   ▼
dist\MediaConv\      ← Python 不要のアプリ一式
   │  + bin\ffmpeg.exe
   │  Inno Setup
   ▼
Output\MediaConv_setup.exe   ← 配布物
```

---

## 方法 1: GitHub Actions で自動ビルド（推奨）

ローカルに Inno Setup も ffmpeg も不要。GitHub 側で全部やる。

1. このフォルダを Git リポジトリにして GitHub に push
2. タグを打って push するだけ：
   ```
   git tag v1.0
   git push origin v1.0
   ```
3. `.github/workflows/build.yml` が自動で実行され、
   - 依存導入 → ffmpeg 自動DL → PyInstaller → Inno Setup → setup.exe 生成
   - **Releases ページに `MediaConv_setup.exe` が添付**される
4. 利用者は Releases から exe をダウンロードしてインストールするだけ

手動実行したい場合は GitHub の Actions タブ → build-installer → "Run workflow"。
（タグ無し実行時は Release には添付されず、Actions の Artifacts から取得できる）

---

## 方法 2: ローカルでビルド

### 1. ffmpeg を `bin\` に置く
静的ビルドの `ffmpeg.exe` を `bin\ffmpeg.exe` に配置（詳細は `bin\README.txt`）。

### 2. Inno Setup を導入（無料）
https://jrsoftware.org/isdl.php → "Inno Setup 6"

### 3. `build.bat` を実行
PyInstaller → Inno Setup を順に実行し、`Output\MediaConv_setup.exe` を生成する。

---

## 仕組み（同梱 ffmpeg の検出）

- `pdf_ops.find_ffmpeg()` … exe と同じフォルダの `bin\ffmpeg.exe` を探す
  （見つからなければ PATH にフォールバック）

インストール後のレイアウト：
```
{app}\
  MediaConv.exe
  _internal\          (PyInstaller のランタイム)
  bin\ffmpeg.exe
```

## メモ
- ffmpeg を同梱しない最小構成にする場合は `bin\` を空にし、
  `installer.iss` の `Source: "bin\*"` 行を削除する（音声変換は無効になる）。
- `dist\` は opencv / PyQt5 / PyMuPDF を含むため 250〜300MB 程度になる。
