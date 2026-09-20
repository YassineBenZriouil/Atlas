"""Settings dialog placeholder (Atlas.md sections 35, 54). Phase 1 only
establishes the shape; Phase 3 fills in every settings category."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ATLAS Settings")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings UI is implemented in a later phase."))
