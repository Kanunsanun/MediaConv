# -*- coding: utf-8 -*-
"""pdftool 用 プロオーディオ風テーマモジュール（UFX-MG / UFX-PC と同系統）。

app.py からは **import するだけ** で配色をプロ機材風に切り替えられる。
GUI 構造（左ナビ＋QStackedWidget＋下部バー）はそのまま、配色とパネル質感だけを
mgfx 系の THEMES に揃える。ノブ/フェーダーは含めない（ファイル変換ソフト向け）。

使い方（app.py 側）:
    from theme import THEMES, build_qss, ToggleSwitch, draw_text_fit

    app.setStyleSheet(build_qss("dark"))      # ← STYLE 定数の置き換え
    # テーマ切替したい場合:  app.setStyleSheet(build_qss("light"))

既存の objectName（nav / primary / ghost / pageTitle / pageDesc / hline /
bottom / log / statusNote）にそのまま対応しているため、app.py の Widget には
手を入れなくても見た目が変わる。
"""
from PyQt5 import QtCore, QtGui, QtWidgets


# ===========================================================================
# 配色（UFX-MG / UFX-PC と同じ集中管理方式）。pdftool 用に nav / 変換ソフト向けの
# キーを追加。メーター/グラフ系キーは持たない（このアプリには無い）。
# ===========================================================================
THEMES = {
    "dark": {
        "win_bg": "#121212", "panel_bg": "#1E1E1E", "panel_border": "#2E2E2E",
        "ctrl_bg": "#2A2A30", "text": "#E0E0E0", "text_dim": "#7A7A7A",
        "accent": "#00ADB5", "accent_dk": "#007E84",
        "accent2": "#FF5722", "accent2_dk": "#C63A12",
        # 左ナビ（本体よりわずかに沈めて段差を出す）
        "nav_bg": "#171717", "nav_text": "#B8BCC4", "nav_hover": "#23232A",
        # ステータス色
        "ok": "#00E676", "warn": "#FFB300", "err": "#FF1744",
        # ログ欄（常に暗）
        "log_bg": "#0A0A0C", "log_text": "#B8B8C0",
        # ON/OFF トグル（自発光式）
        "tog_on_bg": "#15292B", "tog_off_bg": "#202024", "tog_off_fg": "#6A6A72",
    },
    "light": {
        "win_bg": "#ECECEF", "panel_bg": "#FBFBFD", "panel_border": "#D2D2D8",
        "ctrl_bg": "#FFFFFF", "text": "#1A1A20", "text_dim": "#6A6A72",
        "accent": "#0097A7", "accent_dk": "#006978",
        "accent2": "#E64A19", "accent2_dk": "#B23A10",
        "nav_bg": "#232A36", "nav_text": "#C7CDDB", "nav_hover": "#2E3645",
        "ok": "#15803D", "warn": "#B45309", "err": "#D32F2F",
        # ログ欄はライトでも暗いまま（系統維持・視認性確保）
        "log_bg": "#0A0A0C", "log_text": "#B8B8C0",
        "tog_on_bg": "#DAF4F5", "tog_off_bg": "#E6E6E9", "tog_off_fg": "#9A9AA2",
    },
}


def _rgba(hex_color, alpha):
    """'#RRGGBB' と alpha(0-255) → 'rgba(r,g,b,a)'。"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ===========================================================================
# アプリ全体の QSS を生成。pdftool の既存 objectName にそのまま対応。
# ===========================================================================
def build_qss(theme="dark"):
    t = THEMES[theme] if isinstance(theme, str) else theme
    return f"""
* {{ font-family: 'Yu Gothic UI', 'Meiryo', sans-serif; }}
QMainWindow, QWidget {{ background: {t['win_bg']}; color: {t['text']}; }}

/* 左ナビ（本体より沈めた縦リスト・選択はアクセント帯） */
QListWidget#nav {{
    background: {t['nav_bg']}; color: {t['nav_text']}; border: none;
    outline: none; padding-top: 8px; font-size: 13px;
}}
QListWidget#nav::item {{ padding: 11px 14px; border: none; }}
QListWidget#nav::item:selected {{
    background: {t['accent']}; color: #0A0A0A;
    border-left: 3px solid {t['accent2']};
}}
QListWidget#nav::item:hover:!selected {{ background: {t['nav_hover']}; }}

/* ページ見出し */
QLabel#pageTitle {{ font-size: 20px; font-weight: 600; color: {t['text']}; }}
QLabel#pageDesc  {{ color: {t['text_dim']}; font-size: 12px; }}
QLabel#sectionLabel {{ color: {t['text']}; font-weight: bold; }}
QFrame#hline {{ background: {t['panel_border']}; max-height: 1px; border: none; }}

/* パネル枠（GroupBox を機材パネル風に） */
QGroupBox {{
    background: {t['panel_bg']}; border: 1px solid {t['panel_border']};
    border-radius: 6px; margin-top: 18px; font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 10px; padding: 2px 6px; color: {t['text']};
}}

/* 入力系 */
QLineEdit, QComboBox, QSpinBox {{
    background: {t['ctrl_bg']}; color: {t['text']};
    border: 1px solid {t['panel_border']}; border-radius: 6px;
    padding: 6px 8px; min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {t['accent']};
}}
QComboBox QAbstractItemView {{
    background: {t['ctrl_bg']}; color: {t['text']};
    selection-background-color: {t['accent']}; selection-color: #0A0A0A;
}}
QListWidget {{
    background: {t['ctrl_bg']}; color: {t['text']};
    border: 1px solid {t['panel_border']}; border-radius: 6px;
}}
QRadioButton, QCheckBox {{ color: {t['text']}; background: transparent; }}

/* 主ボタン（実行）＝アクセント。プロ機材の点灯ボタン風 */
QPushButton#primary {{
    background: {t['accent']}; color: #0A0A0A; border: none; border-radius: 7px;
    font-size: 14px; font-weight: 700; padding: 8px 16px;
}}
QPushButton#primary:hover    {{ background: {t['accent_dk']}; color: #FFFFFF; }}
QPushButton#primary:disabled {{ background: {t['ctrl_bg']}; color: {t['text_dim']}; }}

/* 副ボタン（参照…など）＝ゴースト */
QPushButton#ghost {{
    background: {t['ctrl_bg']}; color: {t['text']};
    border: 1px solid {t['panel_border']}; border-radius: 6px; padding: 6px 12px;
}}
QPushButton#ghost:hover {{ border-color: {t['accent']}; }}
QPushButton {{
    background: {t['ctrl_bg']}; color: {t['text']};
    border: 1px solid {t['panel_border']}; border-radius: 6px; padding: 6px 12px;
}}
QPushButton:hover {{ border-color: {t['accent']}; }}

/* 下部バー */
QWidget#bottom {{ background: {t['panel_bg']}; border-top: 1px solid {t['panel_border']}; }}

/* プログレス */
QProgressBar {{
    background: {t['ctrl_bg']}; border: 1px solid {t['panel_border']};
    border-radius: 6px; height: 18px; text-align: center; color: {t['text']};
}}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 5px; }}

/* ログ（常に暗いモニタ風） */
QTextEdit#log {{
    background: {t['log_bg']}; color: {t['log_text']}; border: none;
    border-radius: 6px; font-family: 'Consolas', monospace; font-size: 12px;
}}

/* ステータス表示（検出状況など） */
QLabel#statusNote {{ color: {t['text_dim']}; font-size: 12px; }}
QLabel#statusNote[ok="true"]  {{ color: {t['ok']}; }}
QLabel#statusNote[ok="false"] {{ color: {t['warn']}; }}
"""


# ===========================================================================
# テキスト見切れ防止ヘルパー（QFontMetrics 実寸測定 → 収まる最大フォント）。
# UFX-MG から移植。paintEvent で固定 point に頼らず安全に描画したい時に使う。
# ===========================================================================
def draw_text_fit(p, rect, flags, text, max_pt, min_pt=6, bold=True):
    f = p.font()
    f.setBold(bold)
    f.setPointSize(max_pt)
    p.setFont(f)
    br = p.fontMetrics().boundingRect(text)
    if br.width() <= rect.width() and br.height() <= rect.height():
        p.drawText(rect, flags, text)
        return
    scale = min(rect.width() / max(br.width(), 1),
                rect.height() / max(br.height(), 1))
    pt = max(min_pt, int(max_pt * scale))
    f.setPointSize(pt)
    p.setFont(f)
    br = p.fontMetrics().boundingRect(text)
    if br.width() <= rect.width() and br.height() <= rect.height():
        p.drawText(rect, flags, text)
        return
    f.setPointSize(min_pt)
    p.setFont(f)
    elided = p.fontMetrics().elidedText(text, QtCore.Qt.ElideRight, rect.width())
    p.drawText(rect, flags, elided)


# ===========================================================================
# 自発光式 ON/OFF（BYPASS）トグル。UFX-MG / UFX-PC と同じ機材風インジケータ。
#   ON  : 濃い地＋アクセント枠/文字＋点灯ドット（グロー）
#   OFF : 消灯グレー＋off_text
# pdftool では「ZIP でまとめる」「上書き保存」等の真偽切替に転用可。
# ===========================================================================
class ToggleSwitch(QtWidgets.QPushButton):
    def __init__(self, on_text, off_text, theme="dark"):
        super().__init__()
        self.on_text = on_text
        self.off_text = off_text
        self._t = THEMES[theme] if isinstance(theme, str) else theme
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(30)
        mf = QtGui.QFont(); mf.setBold(True); mf.setPointSize(11)
        fm = QtGui.QFontMetrics(mf)
        longest = max(on_text, off_text, key=lambda s: fm.horizontalAdvance(s))
        self.setMinimumWidth(30 + fm.horizontalAdvance(longest) + 18)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.toggled.connect(lambda _=None: self.update())

    def set_theme(self, t):
        self._t = THEMES[t] if isinstance(t, str) else t
        self.update()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        t = self._t
        on = self.isChecked()
        w, h = self.width(), self.height()
        if on:
            bg = QtGui.QColor(t["tog_on_bg"]); fg = QtGui.QColor(t["accent"])
        else:
            bg = QtGui.QColor(t["tog_off_bg"]); fg = QtGui.QColor(t["tog_off_fg"])
        p.setBrush(bg)
        p.setPen(QtGui.QPen(fg, 1.5))
        p.drawRoundedRect(QtCore.QRectF(1, 1, w - 2, h - 2), 7, 7)
        cx = 14.0
        cy = h / 2.0
        dr = max(4.0, h * 0.16)
        p.setPen(QtCore.Qt.NoPen)
        if on:
            glow = QtGui.QColor(t["accent"]); glow.setAlpha(70)
            p.setBrush(glow); p.drawEllipse(QtCore.QPointF(cx, cy), dr * 1.9, dr * 1.9)
            p.setBrush(QtGui.QColor(t["accent"]))
        else:
            p.setBrush(QtGui.QColor(t["tog_off_fg"]))
        p.drawEllipse(QtCore.QPointF(cx, cy), dr, dr)
        txt = self.on_text if on else self.off_text
        p.setPen(fg)
        f = p.font(); f.setBold(True); f.setPointSize(max(8, min(11, h // 3)))
        p.setFont(f)
        p.drawText(QtCore.QRectF(cx + dr + 8, 0, w - (cx + dr + 8) - 8, h),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, txt)


# 動作確認用（このファイル単体で見た目をプレビュー）
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(build_qss("dark"))
    w = QtWidgets.QWidget(); w.resize(360, 200)
    lay = QtWidgets.QVBoxLayout(w)
    lay.addWidget(ToggleSwitch("ZIP ON", "ZIP OFF"))
    b = QtWidgets.QPushButton("実行"); b.setObjectName("primary"); lay.addWidget(b)
    g = QtWidgets.QPushButton("参照…"); g.setObjectName("ghost"); lay.addWidget(g)
    w.show()
    sys.exit(app.exec_())
