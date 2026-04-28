from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)


class DefinitionPopup(QFrame):
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.ToolTip)

        self.setObjectName("definitionPopup")
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setMaximumWidth(360)
        self.label.setMinimumWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(self.label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(80, 60, 45, 45))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(
            """
            QFrame#definitionPopup {
                background: #fffaf3;
                border: 2px solid #eadfce;
                border-radius: 18px;
            }

            QLabel {
                color: #4a3f35;
                font-size: 14px;
                font-weight: 600;
                line-height: 1.45;
            }
            """
        )

    def show_definition(self, *, word: str, text: str, global_pos: QPoint) -> None:
        self.label.setText(
            f"<div style='font-size:16px; font-weight:800; margin-bottom:6px;'>"
            f"{word}"
            f"</div>"
            f"<div style='font-size:14px; font-weight:500;'>"
            f"{text}"
            f"</div>"
        )

        self.adjustSize()

        pos = QPoint(global_pos.x() + 18, global_pos.y() + 18)
        self.move(pos)
        self.show()

    def hide_popup(self) -> None:
        self.hide()