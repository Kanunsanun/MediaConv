# -*- coding: utf-8 -*-
"""PDF 変換のコア処理。GUI から独立した純粋な関数群。

すべて progress(done, total, message) コールバックを受け取り、進捗を通知できる。
外部依存は音声変換の ffmpeg のみ。それ以外は Python 完結（オフライン）。
"""
import os
import io
import shutil
import zipfile
import subprocess

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
def _noop(done, total, msg=""):
    pass


def bundle_dirs():
    """同梱バイナリ(ffmpeg)を探す基準ディレクトリ一覧。

    PyInstaller でフリーズした場合は exe のあるフォルダと _MEIPASS、
    スクリプト実行時はこのファイルのフォルダを返す。
    """
    import sys
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(meipass)
    dirs.append(os.path.dirname(os.path.abspath(__file__)))
    # 重複を除いて返す
    seen = set()
    uniq = []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def zip_files(file_paths, zip_path, remove_originals=True):
    """複数ファイルを 1 つの ZIP にまとめる。"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in file_paths:
            zf.write(p, arcname=os.path.basename(p))
    if remove_originals:
        for p in file_paths:
            try:
                os.remove(p)
            except OSError:
                pass
    return zip_path


def parse_page_ranges(text, page_count):
    """"1-3,5,8-" のような指定を 0-based ページ index のソート済みリストに変換。

    空文字なら全ページ。範囲外は無視。1-based 入力 → 0-based 出力。
    """
    text = (text or "").strip()
    if not text:
        return list(range(page_count))
    pages = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            a = a.strip()
            b = b.strip()
            start = int(a) if a else 1
            end = int(b) if b else page_count
            for p in range(start, end + 1):
                if 1 <= p <= page_count:
                    pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= page_count:
                pages.add(p - 1)
    return sorted(pages)


# ---------------------------------------------------------------------------
# PDF → 画像
# ---------------------------------------------------------------------------
def pdf_to_images(pdf_path, out_dir, dpi=200, fmt="png", pages="",
                  as_zip=True, progress=_noop):
    os.makedirs(out_dir, exist_ok=True)
    fmt = fmt.lower()
    doc = fitz.open(pdf_path)
    try:
        idxs = parse_page_ranges(pages, doc.page_count)
        total = len(idxs)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        stem = _stem(pdf_path)
        outputs = []
        for i, pno in enumerate(idxs):
            page = doc.load_page(pno)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            ext = "jpg" if fmt in ("jpg", "jpeg") else fmt
            out = os.path.join(out_dir, f"{stem}_p{pno + 1:03d}.{ext}")
            if ext == "jpg":
                pix.save(out, jpg_quality=90)
            else:
                pix.save(out)
            outputs.append(out)
            progress(i + 1, total, f"ページ {pno + 1} を書き出し")
        if as_zip and len(outputs) > 1:
            zip_path = os.path.join(out_dir, f"{stem}_images.zip")
            zip_files(outputs, zip_path, remove_originals=True)
            progress(total, total, f"{len(outputs)} 枚を ZIP にまとめました")
            return [zip_path]
        return outputs
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 画像 → PDF
# ---------------------------------------------------------------------------
def images_to_pdf(image_paths, out_pdf, progress=_noop):
    """複数画像を 1 つの PDF にまとめる。各画像 = 1 ページ。"""
    from PIL import Image

    total = len(image_paths)
    doc = fitz.open()
    try:
        for i, img_path in enumerate(image_paths):
            # PIL で開いて回転情報を正規化し、RGB の PNG バイト列に変換
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                w, h = im.size
            rect = fitz.Rect(0, 0, w, h)
            page = doc.new_page(width=w, height=h)
            page.insert_image(rect, stream=buf.getvalue())
            progress(i + 1, total, f"{os.path.basename(img_path)} を追加")
        doc.save(out_pdf)
        return out_pdf
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# PDF → テキスト
# ---------------------------------------------------------------------------
def pdf_to_text(pdf_path, out_txt, pages="", progress=_noop):
    doc = fitz.open(pdf_path)
    try:
        idxs = parse_page_ranges(pages, doc.page_count)
        total = len(idxs)
        chunks = []
        for i, pno in enumerate(idxs):
            page = doc.load_page(pno)
            chunks.append(page.get_text())
            progress(i + 1, total, f"ページ {pno + 1} を抽出")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(chunks))
        return out_txt
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# PDF → Word (docx)
# ---------------------------------------------------------------------------
def _patch_fitz_for_pdf2docx():
    """新しい PyMuPDF (1.26+) で削除された旧 API を pdf2docx 向けに補う。"""
    if not hasattr(fitz.Rect, "get_area"):
        def get_area(self, unit="px"):
            area = abs((self.x1 - self.x0) * (self.y1 - self.y0))
            factor = {"px": 1.0, "in": 1.0 / 72.0, "mm": 25.4 / 72.0,
                      "cm": 2.54 / 72.0}.get(unit, 1.0)
            return area * factor * factor
        fitz.Rect.get_area = get_area


def pdf_to_word(pdf_path, out_docx, progress=_noop):
    _patch_fitz_for_pdf2docx()
    from pdf2docx import Converter

    progress(0, 1, "変換中（時間がかかる場合があります）...")
    cv = Converter(pdf_path)
    try:
        cv.convert(out_docx, start=0, end=None)
    finally:
        cv.close()
    progress(1, 1, "完了")
    return out_docx


# ---------------------------------------------------------------------------
# 結合
# ---------------------------------------------------------------------------
def merge_pdfs(pdf_paths, out_pdf, rotations=None, progress=_noop):
    """複数 PDF を 1 つに結合する。

    rotations は各 PDF に適用する回転角(0/90/180/270)のリスト（pdf_paths と対応）。
    指定があれば、その PDF の全ページを回転してから結合する。
    """
    total = len(pdf_paths)
    doc = fitz.open()
    try:
        for i, p in enumerate(pdf_paths):
            src = fitz.open(p)
            rot = 0 if not rotations else int(rotations[i]) % 360
            if rot:
                for page in src:
                    page.set_rotation((page.rotation + rot) % 360)
            doc.insert_pdf(src)
            src.close()
            tag = f"（{rot}°回転）" if rot else ""
            progress(i + 1, total, f"{os.path.basename(p)} を結合{tag}")
        doc.save(out_pdf)
        return out_pdf
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 分割
# ---------------------------------------------------------------------------
def split_pdf(pdf_path, out_dir, mode="each", every=1, ranges="",
              as_zip=True, progress=_noop):
    """PDF を分割する。

    mode="each"   : 1 ページずつ別ファイル
    mode="every"  : every ページごとにまとめて分割
    mode="ranges" : "1-3,4-6" のような範囲ごとに 1 ファイル
    """
    os.makedirs(out_dir, exist_ok=True)
    stem = _stem(pdf_path)
    doc = fitz.open(pdf_path)
    outputs = []
    try:
        n = doc.page_count
        groups = []  # list of (label, [page indexes])
        if mode == "each":
            groups = [(f"p{p + 1:03d}", [p]) for p in range(n)]
        elif mode == "every":
            every = max(1, int(every))
            for start in range(0, n, every):
                idxs = list(range(start, min(start + every, n)))
                groups.append((f"p{idxs[0] + 1:03d}-{idxs[-1] + 1:03d}", idxs))
        elif mode == "ranges":
            for part in (ranges or "").split(","):
                part = part.strip()
                if not part:
                    continue
                idxs = parse_page_ranges(part, n)
                if idxs:
                    groups.append((f"p{idxs[0] + 1:03d}-{idxs[-1] + 1:03d}", idxs))
        else:
            raise ValueError(f"unknown mode: {mode}")

        total = len(groups)
        for i, (label, idxs) in enumerate(groups):
            new = fitz.open()
            for p in idxs:
                new.insert_pdf(doc, from_page=p, to_page=p)
            out = os.path.join(out_dir, f"{stem}_{label}.pdf")
            new.save(out)
            new.close()
            outputs.append(out)
            progress(i + 1, total, f"{label} を保存")
        if as_zip and len(outputs) > 1:
            zip_path = os.path.join(out_dir, f"{stem}_split.zip")
            zip_files(outputs, zip_path, remove_originals=True)
            progress(total, total, f"{len(outputs)} ファイルを ZIP にまとめました")
            return [zip_path]
        return outputs
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 回転
# ---------------------------------------------------------------------------
def rotate_pdf(pdf_path, out_pdf, angle=90, pages="", progress=_noop):
    doc = fitz.open(pdf_path)
    try:
        idxs = parse_page_ranges(pages, doc.page_count)
        total = len(idxs)
        for i, pno in enumerate(idxs):
            page = doc.load_page(pno)
            page.set_rotation((page.rotation + angle) % 360)
            progress(i + 1, total, f"ページ {pno + 1} を回転")
        doc.save(out_pdf)
        return out_pdf
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 圧縮
# ---------------------------------------------------------------------------
def compress_pdf(pdf_path, out_pdf, image_dpi=120, jpeg_quality=60, progress=_noop):
    """画像を再エンコード（ダウンサンプル）してファイルサイズを削減する。

    テキスト主体の PDF では garbage collection と deflate のみが効く。
    """
    from PIL import Image

    doc = fitz.open(pdf_path)
    try:
        xrefs = set()
        for pno in range(doc.page_count):
            for img in doc.get_page_images(pno):
                xrefs.add(img[0])
        xrefs = sorted(xrefs)
        total = max(1, len(xrefs))

        for i, xref in enumerate(xrefs):
            try:
                base = doc.extract_image(xref)
            except Exception:
                progress(i + 1, total, "")
                continue
            img_bytes = base["image"]
            try:
                im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            except Exception:
                progress(i + 1, total, "")
                continue

            # DPI ベースの目安で長辺を制限（おおまかなダウンサンプル）
            max_side = max(im.size)
            limit = int(image_dpi / 72.0 * 1000)  # ざっくり上限
            if max_side > limit and limit > 0:
                scale = limit / max_side
                im = im.resize((max(1, int(im.width * scale)),
                                max(1, int(im.height * scale))), Image.LANCZOS)

            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=int(jpeg_quality))
            new_bytes = buf.getvalue()
            if len(new_bytes) < len(img_bytes):
                try:
                    doc.update_stream(xref, new_bytes)
                except Exception:
                    pass
            progress(i + 1, total, f"画像 {i + 1}/{len(xrefs)} を圧縮")

        doc.save(out_pdf, garbage=4, deflate=True, clean=True)
        return out_pdf
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# 音声変換 (ffmpeg)
# ---------------------------------------------------------------------------
AUDIO_FORMATS = {
    # 拡張子: (ffmpeg コーデック, 追加オプション)
    "wav":  ["-c:a", "pcm_s16le"],
    "mp3":  ["-c:a", "libmp3lame", "-q:a", "2"],
    "flac": ["-c:a", "flac"],
    "aac":  ["-c:a", "aac", "-b:a", "192k"],
}


def find_ffmpeg():
    """ffmpeg 実行ファイルのパスを返す。見つからなければ None。

    探索順: 同梱フォルダ → PATH。
    """
    for base in bundle_dirs():
        for rel in ("ffmpeg.exe", "ffmpeg/bin/ffmpeg.exe", "bin/ffmpeg.exe"):
            cand = os.path.join(base, rel.replace("/", os.sep))
            if os.path.exists(cand):
                return cand
    return shutil.which("ffmpeg")


def convert_audio(input_paths, out_dir, out_fmt="mp3", progress=_noop):
    """音声ファイルを指定フォーマットに変換する（ffmpeg 使用）。

    out_fmt は AUDIO_FORMATS のキー(wav/mp3/flac/aac)。
    AAC は拡張子 .m4a コンテナで出力する。
    """
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("ffmpeg が見つかりません。")
    out_fmt = out_fmt.lower()
    if out_fmt not in AUDIO_FORMATS:
        raise ValueError(f"未対応の形式: {out_fmt}")
    os.makedirs(out_dir, exist_ok=True)
    ext = "m4a" if out_fmt == "aac" else out_fmt

    total = len(input_paths)
    outputs = []
    for i, src in enumerate(input_paths):
        stem = _stem(src)
        out = os.path.join(out_dir, f"{stem}.{ext}")
        # 入力と出力が同じパスにならないよう調整
        if os.path.abspath(out) == os.path.abspath(src):
            out = os.path.join(out_dir, f"{stem}_conv.{ext}")
        cmd = [ff, "-y", "-i", src] + AUDIO_FORMATS[out_fmt] + [out]
        progress(i, total, f"{os.path.basename(src)} → {ext}")
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              creationflags=_no_window())
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-3:]
            raise RuntimeError(
                f"{os.path.basename(src)} の変換に失敗:\n" + "\n".join(tail))
        outputs.append(out)
        progress(i + 1, total, f"{os.path.basename(out)} を保存")
    return outputs


def _no_window():
    """Windows でサブプロセスのコンソール窓を出さないフラグ。"""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
