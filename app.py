# -*- coding: utf-8 -*-
"""MediaConv — ローカル PDF・音声 変換ツール (PyQt5 GUI)。

機能: PDF↔画像 / PDF→テキスト / PDF→Word / 結合 / 分割 / 回転 / 圧縮 / 音声変換
PDF 系はオフラインで動作。音声変換のみ ffmpeg を使用（配布版は同梱）。
"""
import os
import sys
import traceback

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QListWidget, QListWidgetItem,
    QStackedWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QSpinBox, QComboBox, QProgressBar, QTextEdit,
    QGroupBox, QFormLayout, QMessageBox, QListView, QAbstractItemView, QRadioButton,
    QButtonGroup, QCheckBox, QFrame, QSizePolicy,
)

import pdf_ops as ops
from theme import build_qss

PDF_FILTER = "PDF ファイル (*.pdf)"
IMG_FILTER = "画像 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"
AUDIO_FILTER = "音声 (*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.aiff *.wma)"

PDF_EXTS = (".pdf",)
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")
AUDIO_EXTS = (".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".aiff", ".aif", ".wma")


# ===========================================================================
# バックグラウンド処理ワーカー
# ===========================================================================
class Worker(QThread):
    progress = pyqtSignal(int, int, str)   # done, total, message
    finished_ok = pyqtSignal(object)       # 結果（パス or リスト）
    failed = pyqtSignal(str)

    def __init__(self, func, kwargs):
        super().__init__()
        self.func = func
        self.kwargs = kwargs

    def run(self):
        try:
            def cb(done, total, msg=""):
                self.progress.emit(done, total, msg)
            self.kwargs["progress"] = cb
            result = self.func(**self.kwargs)
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit("".join(
                traceback.format_exception_only(type(e), e)).strip())


# ===========================================================================
# 再利用パーツ
# ===========================================================================
def hline():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setObjectName("hline")
    return f


def _first_dropped_path(event, dirs_ok=True, files_ok=True):
    """ドロップイベントから最初の妥当なローカルパスを返す。なければ None。"""
    md = event.mimeData()
    if not md.hasUrls():
        return None
    for url in md.urls():
        p = url.toLocalFile()
        if not p:
            continue
        if os.path.isdir(p) and dirs_ok:
            return p
        if os.path.isfile(p) and files_ok:
            return p
    return None


class FileDropLineEdit(QLineEdit):
    """ファイル/フォルダのドラッグ&ドロップを受け付ける入力欄。"""
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if _first_dropped_path(e):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if _first_dropped_path(e):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        p = _first_dropped_path(e)
        if p:
            self.setText(p)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class PathRow(QWidget):
    """ラベル + 入力欄 + 参照ボタンの 1 行。入力欄は DnD 対応。"""
    def __init__(self, browse_cb, placeholder=""):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = FileDropLineEdit()
        self.edit.setPlaceholderText(placeholder)
        btn = QPushButton("参照…")
        btn.setObjectName("ghost")
        btn.clicked.connect(browse_cb)
        lay.addWidget(self.edit, 1)
        lay.addWidget(btn)

    def text(self):
        return self.edit.text().strip()

    def set(self, t):
        self.edit.setText(t)


class DropReorderList(QListWidget):
    """内部ドラッグで並べ替え可、かつ外部ファイルのドロップ追加に対応するリスト。"""
    def __init__(self, exts):
        super().__init__()
        self.exts = tuple(e.lower() for e in exts)  # 受け付ける拡張子
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)

    def _external_files(self, event):
        md = event.mimeData()
        if not md.hasUrls():
            return None
        files = []
        for url in md.urls():
            p = url.toLocalFile()
            if os.path.isfile(p) and (not self.exts or p.lower().endswith(self.exts)):
                files.append(p)
        return files or None

    def dragEnterEvent(self, e):
        if e.source() is self:            # 内部並べ替え
            super().dragEnterEvent(e)
        elif self._external_files(e):     # 外部からのファイル追加
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.source() is self:
            super().dragMoveEvent(e)
        elif self._external_files(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e.source() is self:
            super().dropEvent(e)          # 並べ替えは標準処理
            return
        files = self._external_files(e)
        if files:
            for f in files:
                self.addItem(f)
            e.acceptProposedAction()
        else:
            e.ignore()


class FileListWidget(QWidget):
    """複数ファイルを並べ替え可能なリスト + 追加/削除/上下ボタン。

    リスト内でのドラッグ&ドロップ並べ替え、外部ファイルのドロップ追加に対応。
    """
    def __init__(self, file_filter, exts=()):
        super().__init__()
        self.file_filter = file_filter
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = DropReorderList(exts)
        self.list.setMinimumHeight(150)
        lay.addWidget(self.list, 1)

        col = QVBoxLayout()
        for label, slot in [("追加…", self.add), ("削除", self.remove),
                            ("▲", self.up), ("▼", self.down), ("クリア", self.clear)]:
            b = QPushButton(label)
            b.setObjectName("ghost")
            b.clicked.connect(slot)
            col.addWidget(b)
        col.addStretch(1)
        lay.addLayout(col)

    def add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "ファイルを選択", "", self.file_filter)
        for f in files:
            self.list.addItem(f)

    def remove(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))

    def _move(self, delta):
        row = self.list.currentRow()
        if row < 0:
            return
        new = row + delta
        if 0 <= new < self.list.count():
            it = self.list.takeItem(row)
            self.list.insertItem(new, it)
            self.list.setCurrentRow(new)

    def up(self):
        self._move(-1)

    def down(self):
        self._move(1)

    def clear(self):
        self.list.clear()

    def paths(self):
        return [self.list.item(i).text() for i in range(self.list.count())]


# ===========================================================================
# 各機能ページの基底
# ===========================================================================
class Page(QWidget):
    title = "ページ"
    desc = ""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(28, 24, 28, 24)
        self.outer.setSpacing(14)

        head = QLabel(self.title)
        head.setObjectName("pageTitle")
        self.outer.addWidget(head)
        if self.desc:
            d = QLabel(self.desc)
            d.setObjectName("pageDesc")
            d.setWordWrap(True)
            self.outer.addWidget(d)
        self.outer.addWidget(hline())

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignRight)
        self.form.setHorizontalSpacing(16)
        self.form.setVerticalSpacing(12)
        self.outer.addLayout(self.form)
        self.build()
        self.outer.addStretch(1)

        self.run_btn = QPushButton("実行")
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self.on_run)
        self.outer.addWidget(self.run_btn)

    # サブクラスが実装
    def build(self):
        pass

    def make_job(self):
        """(func, kwargs) を返す。検証エラー時は ValueError を投げる。"""
        raise NotImplementedError

    # --- 実行フロー ---
    def on_run(self):
        try:
            func, kwargs = self.make_job()
        except ValueError as e:
            QMessageBox.warning(self, "入力エラー", str(e))
            return
        self.main.start_job(func, kwargs, self.run_btn)

    # 入力補助
    def need(self, value, msg):
        if not value:
            raise ValueError(msg)
        return value

    def default_out(self, src, suffix, ext):
        base = os.path.splitext(src)[0]
        return f"{base}{suffix}.{ext}"


# ---- 各ページ実装 --------------------------------------------------------
class PdfToImagesPage(Page):
    title = "PDF → 画像"
    desc = "PDF の各ページを PNG / JPG 画像に書き出します。"

    def build(self):
        self.src = PathRow(self.pick_src, "変換する PDF")
        self.outdir = PathRow(self.pick_out, "出力先フォルダ")
        self.fmt = QComboBox(); self.fmt.addItems(["png", "jpg"])
        self.dpi = QSpinBox(); self.dpi.setRange(36, 600); self.dpi.setValue(200)
        self.pages = QLineEdit(); self.pages.setPlaceholderText("例: 1-3,5  (空=全ページ)")
        self.zip = QCheckBox("複数枚になる場合は ZIP にまとめて出力")
        self.zip.setChecked(True)
        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力フォルダ", self.outdir)
        self.form.addRow("形式", self.fmt)
        self.form.addRow("解像度 (DPI)", self.dpi)
        self.form.addRow("ページ", self.pages)
        self.form.addRow("", self.zip)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            if not self.outdir.text():
                self.outdir.set(os.path.dirname(f))

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        if d:
            self.outdir.set(d)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.outdir.text(), "出力フォルダを選択してください。")
        return ops.pdf_to_images, dict(
            pdf_path=src, out_dir=out, dpi=self.dpi.value(),
            fmt=self.fmt.currentText(), pages=self.pages.text(),
            as_zip=self.zip.isChecked())


class ImagesToPdfPage(Page):
    title = "画像 → PDF"
    desc = "複数の画像を 1 つの PDF にまとめます（リストの順番がページ順）。"

    def build(self):
        self.files = FileListWidget(IMG_FILTER, IMG_EXTS)
        self.out = PathRow(self.pick_out, "出力 PDF")
        self.form.addRow("画像ファイル", self.files)
        self.form.addRow("出力 PDF", self.out)

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "images.pdf", PDF_FILTER)
        if f:
            self.out.set(f)

    def make_job(self):
        paths = self.files.paths()
        if not paths:
            raise ValueError("画像を 1 つ以上追加してください。")
        out = self.need(self.out.text(), "出力 PDF を指定してください。")
        return ops.images_to_pdf, dict(image_paths=paths, out_pdf=out)


class PdfToTextPage(Page):
    title = "PDF → テキスト"
    desc = "PDF 内の文字を抽出してテキストファイルに保存します（テキストとして埋め込まれた文字が対象）。"

    def build(self):
        self.src = PathRow(self.pick_src, "入力 PDF")
        self.out = PathRow(self.pick_out, "出力 .txt")
        self.pages = QLineEdit(); self.pages.setPlaceholderText("例: 1-3,5  (空=全ページ)")
        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力 TXT", self.out)
        self.form.addRow("ページ", self.pages)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            self.out.set(self.default_out(f, "", "txt"))

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "", "テキスト (*.txt)")
        if f:
            self.out.set(f)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.out.text(), "出力 TXT を指定してください。")
        return ops.pdf_to_text, dict(pdf_path=src, out_txt=out, pages=self.pages.text())


class PdfToWordPage(Page):
    title = "PDF → Word"
    desc = "PDF を編集可能な Word (.docx) に変換します。レイアウト保持を試みます。"

    def build(self):
        self.src = PathRow(self.pick_src, "入力 PDF")
        self.out = PathRow(self.pick_out, "出力 .docx")
        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力 DOCX", self.out)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            self.out.set(self.default_out(f, "", "docx"))

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "", "Word (*.docx)")
        if f:
            self.out.set(f)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.out.text(), "出力 DOCX を指定してください。")
        return ops.pdf_to_word, dict(pdf_path=src, out_docx=out)


class MergePage(Page):
    title = "結合"
    desc = "複数の PDF を 1 つにまとめます。リストの行をドラッグして順番を入れ替えられます（上から順に結合）。"

    def build(self):
        self.files = FileListWidget(PDF_FILTER, PDF_EXTS)
        self.out = PathRow(self.pick_out, "出力 PDF")
        self.form.addRow("PDF ファイル", self.files)
        self.form.addRow("出力 PDF", self.out)

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "merged.pdf", PDF_FILTER)
        if f:
            self.out.set(f)

    def make_job(self):
        paths = self.files.paths()
        if len(paths) < 2:
            raise ValueError("PDF を 2 つ以上追加してください。")
        out = self.need(self.out.text(), "出力 PDF を指定してください。")
        return ops.merge_pdfs, dict(pdf_paths=paths, out_pdf=out)


class SplitPage(Page):
    title = "分割"
    desc = "PDF を複数ファイルに分割します。"

    def build(self):
        self.src = PathRow(self.pick_src, "入力 PDF")
        self.outdir = PathRow(self.pick_out, "出力先フォルダ")

        self.mode_group = QButtonGroup(self)
        self.rb_each = QRadioButton("1 ページずつ")
        self.rb_every = QRadioButton("N ページごと")
        self.rb_ranges = QRadioButton("範囲指定")
        self.rb_each.setChecked(True)
        for rb in (self.rb_each, self.rb_every, self.rb_ranges):
            self.mode_group.addButton(rb)
        mode_box = QVBoxLayout()
        mode_box.addWidget(self.rb_each)
        row_every = QHBoxLayout()
        row_every.addWidget(self.rb_every)
        self.every = QSpinBox(); self.every.setRange(1, 9999); self.every.setValue(2)
        row_every.addWidget(self.every); row_every.addWidget(QLabel("ページごと")); row_every.addStretch(1)
        mode_box.addLayout(row_every)
        row_ranges = QHBoxLayout()
        row_ranges.addWidget(self.rb_ranges)
        self.ranges = QLineEdit(); self.ranges.setPlaceholderText("例: 1-3,4-6,7")
        row_ranges.addWidget(self.ranges, 1)
        mode_box.addLayout(row_ranges)
        mw = QWidget(); mw.setLayout(mode_box)

        self.zip = QCheckBox("複数ファイルになる場合は ZIP にまとめて出力")
        self.zip.setChecked(True)

        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力フォルダ", self.outdir)
        self.form.addRow("分割方法", mw)
        self.form.addRow("", self.zip)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            if not self.outdir.text():
                self.outdir.set(os.path.dirname(f))

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        if d:
            self.outdir.set(d)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.outdir.text(), "出力フォルダを選択してください。")
        if self.rb_each.isChecked():
            mode = "each"
        elif self.rb_every.isChecked():
            mode = "every"
        else:
            mode = "ranges"
            if not self.ranges.text().strip():
                raise ValueError("範囲を入力してください（例: 1-3,4-6）。")
        return ops.split_pdf, dict(
            pdf_path=src, out_dir=out, mode=mode,
            every=self.every.value(), ranges=self.ranges.text(),
            as_zip=self.zip.isChecked())


class RotatePage(Page):
    title = "回転"
    desc = "指定したページを回転します。"

    def build(self):
        self.src = PathRow(self.pick_src, "入力 PDF")
        self.out = PathRow(self.pick_out, "出力 PDF")
        self.angle = QComboBox(); self.angle.addItems(["90° 右", "180°", "90° 左 (270°)"])
        self.pages = QLineEdit(); self.pages.setPlaceholderText("例: 1-3,5  (空=全ページ)")
        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力 PDF", self.out)
        self.form.addRow("回転角", self.angle)
        self.form.addRow("ページ", self.pages)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            self.out.set(self.default_out(f, "_rotated", "pdf"))

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "", PDF_FILTER)
        if f:
            self.out.set(f)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.out.text(), "出力 PDF を指定してください。")
        angle = {0: 90, 1: 180, 2: 270}[self.angle.currentIndex()]
        return ops.rotate_pdf, dict(pdf_path=src, out_pdf=out, angle=angle, pages=self.pages.text())


class CompressPage(Page):
    title = "圧縮"
    desc = "画像を再エンコードしてファイルサイズを削減します（写真・スキャン PDF に有効）。"

    def build(self):
        self.src = PathRow(self.pick_src, "入力 PDF")
        self.out = PathRow(self.pick_out, "出力 PDF")
        self.quality = QSpinBox(); self.quality.setRange(20, 95); self.quality.setValue(60)
        self.dpi = QSpinBox(); self.dpi.setRange(50, 600); self.dpi.setValue(120)
        self.form.addRow("入力 PDF", self.src)
        self.form.addRow("出力 PDF", self.out)
        self.form.addRow("JPEG 品質", self.quality)
        self.form.addRow("画像 DPI 目安", self.dpi)

    def pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDF を選択", "", PDF_FILTER)
        if f:
            self.src.set(f)
            self.out.set(self.default_out(f, "_compressed", "pdf"))

    def pick_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "保存先", "", PDF_FILTER)
        if f:
            self.out.set(f)

    def make_job(self):
        src = self.need(self.src.text(), "入力 PDF を選択してください。")
        out = self.need(self.out.text(), "出力 PDF を指定してください。")
        return ops.compress_pdf, dict(
            pdf_path=src, out_pdf=out,
            image_dpi=self.dpi.value(), jpeg_quality=self.quality.value())


class AudioPage(Page):
    title = "音声変換"
    desc = "音声ファイルを WAV / MP3 / FLAC / AAC に変換します（複数まとめて変換可）。"

    def build(self):
        self.files = FileListWidget(AUDIO_FILTER, AUDIO_EXTS)
        self.outdir = PathRow(self.pick_out, "出力先フォルダ")
        self.fmt = QComboBox()
        self.fmt.addItems(["wav", "mp3", "flac", "aac"])
        self.status = QLabel()
        self.status.setObjectName("statusNote")
        self.status.setWordWrap(True)
        self.form.addRow("音声ファイル", self.files)
        self.form.addRow("出力フォルダ", self.outdir)
        self.form.addRow("出力形式", self.fmt)
        self.form.addRow("", self.status)
        self.refresh_ffmpeg()

    def refresh_ffmpeg(self):
        ff = ops.find_ffmpeg()
        if ff:
            self.status.setText(f"✓ ffmpeg 検出: {ff}")
            self.status.setProperty("ok", True)
        else:
            self.status.setText(
                "⚠ ffmpeg が見つかりません。音声変換には ffmpeg が必要です"
                "（インストーラ同梱版では自動検出されます）。")
            self.status.setProperty("ok", False)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh_ffmpeg()

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        if d:
            self.outdir.set(d)

    def make_job(self):
        if not ops.find_ffmpeg():
            raise ValueError("ffmpeg が見つかりません。")
        paths = self.files.paths()
        if not paths:
            raise ValueError("音声ファイルを 1 つ以上追加してください。")
        out = self.outdir.text() or os.path.dirname(paths[0])
        return ops.convert_audio, dict(
            input_paths=paths, out_dir=out, out_fmt=self.fmt.currentText())


# ===========================================================================
# メインウィンドウ
# ===========================================================================
class MainWindow(QMainWindow):
    DEFAULT_THEME = "dark"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediaConv — PDF・音声 変換ツール")
        self.resize(940, 680)
        self.worker = None
        self.theme = self.DEFAULT_THEME

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # サイドバー
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(190)
        self.stack = QStackedWidget()

        self.pages = [
            PdfToImagesPage(self), ImagesToPdfPage(self), PdfToTextPage(self),
            PdfToWordPage(self), MergePage(self), SplitPage(self),
            RotatePage(self), CompressPage(self), AudioPage(self),
        ]
        icons = ["🖼", "📄", "🔤", "📝", "🔗", "✂", "🔄", "🗜", "🎵"]
        for ic, p in zip(icons, self.pages):
            QListWidgetItem(f"  {ic}  {p.title}", self.nav)
            self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        body_w = QWidget(); body_w.setLayout(body)
        root.addWidget(body_w, 1)

        # 下部: 進捗 + ログ + テーマ切替
        bottom = QWidget(); bottom.setObjectName("bottom")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(20, 10, 20, 12)

        top_row = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setTextVisible(True)
        self.bar.setValue(0)
        top_row.addWidget(self.bar, 1)
        top_row.addWidget(QLabel("テーマ"))
        self.theme_box = QComboBox()
        self.theme_box.addItems(["dark", "light"])
        self.theme_box.setCurrentText(self.theme)
        self.theme_box.setFixedWidth(90)
        self.theme_box.currentTextChanged.connect(self.change_theme)
        top_row.addWidget(self.theme_box)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(90)
        self.log.setObjectName("log")
        bl.addLayout(top_row)
        bl.addWidget(self.log)
        root.addWidget(bottom)

        self.setCentralWidget(central)
        self.log_msg("準備完了。左のメニューから機能を選んでください。")

    # --- ジョブ制御 ---
    def start_job(self, func, kwargs, btn):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "実行中", "処理が完了するまでお待ちください。")
            return
        self._active_btn = btn
        btn.setEnabled(False)
        self.bar.setValue(0)
        self.log_msg(f"▶ {func.__name__} を開始")
        self.worker = Worker(func, kwargs)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_ok.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, done, total, msg):
        if total > 0:
            self.bar.setMaximum(total)
            self.bar.setValue(done)
            self.bar.setFormat(f"{done}/{total}  %p%")
        if msg:
            self.log_msg(f"  {msg}")

    def on_done(self, result):
        self._active_btn.setEnabled(True)
        self.bar.setFormat("完了  %p%")
        if isinstance(result, list):
            self.log_msg(f"✓ 完了: {len(result)} ファイルを書き出しました。")
            if result:
                self.log_msg(f"  出力先: {os.path.dirname(result[0])}")
        else:
            self.log_msg(f"✓ 完了: {result}")
        QMessageBox.information(self, "完了", "処理が完了しました。")

    def on_failed(self, err):
        self._active_btn.setEnabled(True)
        self.bar.setFormat("エラー")
        self.log_msg(f"✗ エラー: {err}")
        QMessageBox.critical(self, "エラー", err)

    def log_msg(self, text):
        self.log.append(text)

    def change_theme(self, name):
        """テーマを切り替えてアプリ全体のスタイルを再適用する。"""
        self.theme = name
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_qss(name))
        # [ok] プロパティ依存のステータス色を再評価させる
        for page in self.pages:
            note = getattr(page, "status", None)
            if note is not None:
                note.style().unpolish(note)
                note.style().polish(note)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(build_qss(MainWindow.DEFAULT_THEME))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
