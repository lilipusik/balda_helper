from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget


class HoverTreeWidget(QTreeWidget):
    mouse_left = Signal()

    def leaveEvent(self, event) -> None:
        self.mouse_left.emit()
        super().leaveEvent(event)