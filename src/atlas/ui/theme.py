"""Colors and the one stylesheet for the ATLAS window."""

from __future__ import annotations

COLORS = {
    "bg": "#15171a",
    "panel": "#1d2024",
    "raised": "#262a2f",
    "border": "#30353b",
    "text": "#e6e8eb",
    "muted": "#8b939c",
    "accent": "#e0a458",  # warm amber: the one brand color
    "ok": "#6cc08b",
    "fail": "#e46c6c",
    "warn_bg": "#3a2f1c",
}

# Orb color per voice status (`status` events from the voice loop).
STATUS_COLORS = {
    "sleeping": "#4b525a",
    "listening": COLORS["accent"],
    "recognizing": COLORS["accent"],
    "processing": "#7aa7e0",
    "off": "#2c3035",
    "offline": COLORS["fail"],
}

STATUS_TEXT = {
    "sleeping": "Waiting for the wake word",
    "listening": "Listening…",
    "recognizing": "Recognizing…",
    "processing": "Working on it…",
    "off": "Voice is off",
    "offline": "Not connected",
}


def stylesheet() -> str:
    c = COLORS
    return f"""
    QWidget {{ background: {c["bg"]}; color: {c["text"]}; font-size: 10pt; }}
    QLabel {{ background: transparent; }}
    QLabel[role="muted"] {{ color: {c["muted"]}; }}
    QLabel[role="title"] {{ font-size: 15pt; font-weight: 600; }}
    QLabel[role="state"] {{ font-size: 13pt; font-weight: 600; }}
    QFrame[role="panel"] {{
        background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 8px;
    }}
    QFrame[role="banner"] {{
        background: {c["warn_bg"]}; border: 1px solid {c["accent"]}; border-radius: 8px;
    }}
    QWidget#sidebar {{ background: {c["panel"]}; border-right: 1px solid {c["border"]}; }}
    QListWidget#nav {{ background: transparent; border: none; padding-top: 4px; outline: none; }}
    QListWidget#nav::item {{ padding: 9px 16px; border-radius: 6px; margin: 1px 8px; }}
    QListWidget#nav::item:selected {{ background: {c["raised"]}; color: {c["accent"]}; }}
    QListWidget#nav::item:hover:!selected {{ background: {c["raised"]}; }}
    QPushButton {{
        background: {c["raised"]}; border: 1px solid {c["border"]}; border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{ border-color: {c["muted"]}; }}
    QPushButton:pressed {{ background: {c["border"]}; }}
    QPushButton:disabled {{ color: {c["muted"]}; }}
    QPushButton[role="primary"] {{ background: {c["accent"]}; color: #1a1408; border: none; }}
    QPushButton[role="primary"]:hover {{ background: #ebb575; }}
    QPushButton[role="danger"] {{ color: {c["fail"]}; }}
    QPushButton:checked {{ background: {c["accent"]}; color: #1a1408; border: none; }}
    QLineEdit, QComboBox, QDoubleSpinBox, QPlainTextEdit {{
        background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 6px;
        padding: 5px 8px; selection-background-color: {c["accent"]};
        selection-color: #1a1408;
    }}
    QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{ border-color: {c["accent"]}; }}
    QTreeWidget, QTableWidget {{
        background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 8px;
        alternate-background-color: #202328; gridline-color: {c["border"]};
    }}
    QHeaderView::section {{
        background: {c["panel"]}; color: {c["muted"]}; border: none;
        border-bottom: 1px solid {c["border"]}; padding: 6px;
    }}
    QTreeWidget::item, QTableWidget::item {{ padding: 4px; }}
    QTreeWidget::item:selected, QTableWidget::item:selected {{
        background: {c["raised"]}; color: {c["text"]};
    }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    QStatusBar {{ color: {c["muted"]}; }}
    """
