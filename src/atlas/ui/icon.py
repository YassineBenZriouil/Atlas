"""Programmatically drawn tray icon (Atlas.md section 34) - no external
asset file needed, and each state gets its own color without shipping
multiple icon files. `QSystemTrayIcon` with an empty `QIcon()` renders
nothing (Qt logs "No Icon set" and Windows won't show a usable tray
entry), so a real icon here isn't cosmetic - it's required."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

_STATE_COLORS: dict[str, str] = {
    "SLEEPING": "#4a5568",
    "WAKE_DETECTED": "#3182ce",
    "LISTENING": "#3182ce",
    "RECOGNIZING": "#3182ce",
    "PARSING": "#3182ce",
    "VALIDATING": "#3182ce",
    "EXECUTING": "#38a169",
    "FEEDBACK": "#38a169",
    "ERROR": "#e53e3e",
    "RECOVERY": "#e53e3e",
    "DISABLED": "#718096",
}


def build_icon(state_name: str = "SLEEPING", size: int = 64) -> QIcon:
    color = QColor(_STATE_COLORS.get(state_name, "#4a5568"))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)

    painter.setPen(QColor("white"))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.55))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()

    return QIcon(pixmap)
