from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QBrush,
    QMouseEvent,
)
from PySide6.QtWidgets import QWidget


class UsedWordsCloud(QWidget):
    word_clicked = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self.words: list[str] = []
        self.word_rects: dict[str, QRect] = {}
        self.hovered_word: str | None = None

        self.setMouseTracking(True)
        self.setMinimumHeight(90)
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#fffaf0"))
        self.setPalette(palette)

    def set_words(self, words: list[str]) -> None:
        self.words = words
        self.hovered_word = None
        self.word_rects.clear()

        self._update_height()
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        width = max(self.width(), 260)
        height = self._calculate_height(width)
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        width = 260
        height = self._calculate_height(width)
        return QSize(width, height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_height()

    def _update_height(self) -> None:
        width = max(self.width(), 260)
        height = self._calculate_height(width)
        self.setMinimumHeight(height)

    def _calculate_height(self, width: int) -> int:
        if not self.words:
            return 90

        font_metrics = self.fontMetrics()

        x = 12
        y = 12
        row_height = 34
        gap = 8
        max_width = max(width - 24, 100)

        for word in self.words:
            chip_width = font_metrics.horizontalAdvance(word) + 24

            if x + chip_width > max_width + 12:
                x = 12
                y += row_height + gap

            x += chip_width + gap

        return y + row_height + 12

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.word_rects.clear()

        if not self.words:
            painter.setPen(QColor("#9a8b7d"))
            painter.drawText(
                self.rect().adjusted(12, 12, -12, -12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                "Использованные слова появятся здесь...",
            )
            return

        font_metrics = painter.fontMetrics()

        x = 12
        y = 12
        row_height = 34
        gap = 8
        max_width = max(self.width() - 24, 100)

        for word in self.words:
            chip_width = font_metrics.horizontalAdvance(word) + 24

            if x + chip_width > max_width + 12:
                x = 12
                y += row_height + gap

            rect = QRect(x, y, chip_width, row_height)
            self.word_rects[word] = rect

            if word == self.hovered_word:
                background = QColor("#d8f3dc")
                border = QColor("#95d5b2")
                text_color = QColor("#2d4a36")
            else:
                background = QColor("#fffaf0")
                border = QColor("#eadfce")
                text_color = QColor("#4a3f35")

            painter.setPen(QPen(border, 2))
            painter.setBrush(QBrush(background))
            painter.drawRoundedRect(rect, 14, 14)

            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, word)

            x += chip_width + gap

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        word = self._word_at(event.pos())

        if word != self.hovered_word:
            self.hovered_word = word
            self.update()

        if word is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.hovered_word = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        word = self._word_at(event.pos())

        if word is not None:
            self.word_clicked.emit(word)

        super().mousePressEvent(event)

    def _word_at(self, point: QPoint) -> str | None:
        for word, rect in self.word_rects.items():
            if rect.contains(point):
                return word

        return None