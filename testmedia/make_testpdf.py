# -*- coding: utf-8 -*-
"""MediaConv 動作確認用のテスト PDF（A4 1ページ・日本語/英語/数字/数式混在）を生成する。

外部フォント不要（PyMuPDF 内蔵の日本語フォント "japan" を使用）。
実行:  ..\.venv\Scripts\python.exe make_testpdf.py
"""
import os
import fitz

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_document.pdf")
FONT = "japan"  # PyMuPDF 内蔵 CJK フォント

TITLE = "テストドキュメント — MediaConv 動作確認用 / Test Document"

BODY = """\
── 1. 日本語 (Japanese) ──
吾輩は猫である。名前はまだ無い。どこで生まれたか
とんと見当がつかぬ。本書は日本語・英語・数字・数式が
混在したテキスト抽出の確認用サンプルです。ひらがな・
カタカナ・漢字（難読：鬱、薔薇、檸檬、憂鬱）も含みます。

── 2. English ──
The quick brown fox jumps over the lazy dog.
Pack my box with five dozen liquor jugs.
Mixed casing and punctuation: ABCdef, XYZ! (test) 100%.

── 3. 数字・記号 (Numbers) ──
整数: 0 1 2 3 4 5 6 7 8 9
桁区切り: 1,234,567,890   小数: 3.14159265, 2.71828
割合/通貨: 45.6%  ¥12,800  $2,500  €99  £75
日付/時刻: 2026-06-30  01:23:45   負数: -273.15
指数表記: 6.022 × 10^23,  1.6 × 10^-19

── 4. 数式 (Mathematics) ──
ピタゴラスの定理: a² + b² = c²
展開公式: (x + y)² = x² + 2xy + y²
二次方程式の解: x = (-b ± √(b² - 4ac)) / 2a
総和: Σ(k=1..n) k = n(n + 1) / 2
積分: ∫ e^(-x) dx  (0→∞) = 1
極限: lim (1 + 1/n)^n = e   (n → ∞)
不等式: α ≤ β ≠ γ ≥ δ,   |x| ≥ 0,   0 < ε ≪ 1
定数: π ≈ 3.14159,  e ≈ 2.71828,  √2 ≈ 1.41421

── 5. 混在文 (Mixed) ──
半径 r = 5 cm の円の面積は S = πr² ≈ 78.54 cm²。
The temperature was 20°C (68°F) at 3:00 PM on 2026/06/30.
angle θ = 45°,  sin θ ≈ 0.707,  cos 60° = 0.5.
"""


def main():
    doc = fitz.open()
    page = doc.new_page()  # A4 (595 x 842 pt)
    W, H = page.rect.width, page.rect.height
    m = 55

    # タイトル
    page.insert_textbox(fitz.Rect(m, 42, W - m, 92), TITLE,
                        fontname=FONT, fontsize=14, align=fitz.TEXT_ALIGN_LEFT)
    # 区切り線
    page.draw_line(fitz.Point(m, 96), fitz.Point(W - m, 96),
                   color=(0.4, 0.4, 0.4), width=0.8)
    # 本文
    leftover = page.insert_textbox(
        fitz.Rect(m, 108, W - m, H - 50), BODY,
        fontname=FONT, fontsize=10.5, lineheight=1.5,
        align=fitz.TEXT_ALIGN_LEFT)
    # フッター
    page.insert_textbox(fitz.Rect(m, H - 44, W - m, H - 28),
                        "MediaConv test PDF — page 1 / 1",
                        fontname=FONT, fontsize=8, color=(0.5, 0.5, 0.5))

    doc.save(OUT)
    doc.close()
    print("saved:", OUT)
    print("leftover space (>=0 = 収まった):", round(leftover, 1))


if __name__ == "__main__":
    main()
