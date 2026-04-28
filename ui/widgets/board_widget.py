from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPolygon,
    QKeyEvent,
)
from PySide6.QtWidgets import QFrame, QGridLayout, QLineEdit

from solver.hints import SuggestedMove

class BoardCell(QLineEdit):
    move_requested = Signal(int, int)
    edited_by_user = Signal()
    clicked = Signal(int, int)

    def __init__(self, row: int, col: int) -> None:
        super().__init__()

        self.row = row
        self.col = col

        self.setMaxLength(1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.setFixedSize(54, 54)

        self.set_normal_style()

        self.textChanged.connect(self._on_text_changed)
        self.textEdited.connect(self._on_text_edited_by_user)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.row, self.col)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_Left:
            self.move_requested.emit(self.row, self.col - 1)
            return

        if key == Qt.Key.Key_Right:
            self.move_requested.emit(self.row, self.col + 1)
            return

        if key == Qt.Key.Key_Up:
            self.move_requested.emit(self.row - 1, self.col)
            return

        if key == Qt.Key.Key_Down:
            self.move_requested.emit(self.row + 1, self.col)
            return

        super().keyPressEvent(event)

    def _on_text_changed(self, text: str) -> None:
        text = text.strip().lower().replace("ё", "е")

        if len(text) > 1:
            text = text[-1]

        if text and not ("а" <= text <= "я"):
            text = ""

        if self.text() != text:
            self.setText(text)

    def _on_text_edited_by_user(self, _text: str) -> None:
        self.edited_by_user.emit()

    def value(self) -> str:
        return self.text().strip().lower().replace("ё", "е")

    def set_value_silent(self, value: str) -> None:
        self.blockSignals(True)
        self.setText(value)
        self.blockSignals(False)

    def set_normal_style(self) -> None:
        self.setStyleSheet(
            """
            QLineEdit {
                background: #fffaf0;
                border: 2px solid #eadfce;
                border-radius: 14px;
                color: #4a3f35;
                selection-background-color: #f5cfcf;
            }

            QLineEdit:focus {
                border: 2px solid #d8a7b1;
                background: #fff6e8;
            }
            """
        )

    def set_path_style(self, step_index: int) -> None:
        self.setStyleSheet(
            """
            QLineEdit {
                background: #d8f3dc;
                border: 3px solid #95d5b2;
                border-radius: 14px;
                color: #2d4a36;
                font-weight: bold;
            }
            """
        )

        self.setToolTip(f"Шаг {step_index}")

    def set_placed_style(self) -> None:
        self.setStyleSheet(
            """
            QLineEdit {
                background: #ffd6e0;
                border: 3px solid #ff9aae;
                border-radius: 14px;
                color: #6d2e46;
                font-weight: bold;
            }
            """
        )

        self.setToolTip("Новая буква")


class BoardWidget(QFrame):
    board_edited = Signal()
    cell_clicked = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("boardHolder")

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setSpacing(8)

        self.cells: list[list[BoardCell]] = []
        self.arrow_path: list[tuple[int, int]] = []

    def _on_cell_clicked(self, row: int, col: int) -> None:
        self.cell_clicked.emit(row, col)

    def rebuild(self, size: int, old_values: list[list[str]]) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)

            if item is None:
                continue

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.cells = []
        self.arrow_path = []

        for row in range(size):
            row_cells: list[BoardCell] = []

            for col in range(size):
                cell = BoardCell(row, col)
                cell.move_requested.connect(self.focus_cell)
                cell.edited_by_user.connect(self.board_edited.emit)
                cell.clicked.connect(self._on_cell_clicked)

                if row < len(old_values) and col < len(old_values[row]):
                    cell.setText(old_values[row][col])

                self.grid_layout.addWidget(cell, row, col)
                row_cells.append(cell)

            self.cells.append(row_cells)

        self.update()

    def focus_cell(self, row: int, col: int) -> None:
        if not self.cells:
            return

        if not (0 <= row < len(self.cells)):
            return

        if not (0 <= col < len(self.cells[row])):
            return

        cell = self.cells[row][col]
        cell.setFocus()
        cell.selectAll()

    def grid_values(self) -> list[list[str]]:
        return [[cell.value() for cell in row] for row in self.cells]

    def restore_grid(self, grid: list[list[str]]) -> None:
        for row_index, row in enumerate(self.cells):
            for col_index, cell in enumerate(row):
                cell.set_value_silent(grid[row_index][col_index])
                cell.set_normal_style()
                cell.setToolTip("")

        self.arrow_path = []
        self.update()

    def clear_values(self) -> None:
        self.arrow_path = []

        for row in self.cells:
            for cell in row:
                cell.set_value_silent("")
                cell.set_normal_style()
                cell.setToolTip("")

        self.update()

    def clear_highlight(self) -> None:
        self.arrow_path = []

        for row in self.cells:
            for cell in row:
                cell.set_normal_style()
                cell.setToolTip("")

        self.update()

    def show_move(self, move: SuggestedMove, base_grid: list[list[str]]) -> None:
        self.restore_grid(base_grid)

        self.arrow_path = [(cell.row, cell.col) for cell in move.path]

        for step_index, cell in enumerate(move.path, start=1):
            ui_cell = self.cells[cell.row][cell.col]
            ui_cell.set_path_style(step_index)

            original_value = base_grid[cell.row][cell.col]

            if not original_value:
                ui_cell.set_value_silent(move.letter)

        placed_cell = self.cells[move.placed_cell.row][move.placed_cell.col]
        placed_cell.set_value_silent(move.letter)
        placed_cell.set_placed_style()

        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if len(self.arrow_path) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("#6fbf8f"), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor("#6fbf8f")))

        for first, second in zip(self.arrow_path, self.arrow_path[1:]):
            start = self._cell_center(*first)
            end = self._cell_center(*second)

            self._draw_arrow(painter, start, end)

    def _cell_center(self, row: int, col: int) -> QPoint:
        cell = self.cells[row][col]

        local_center = cell.rect().center()
        return cell.mapTo(self, local_center)

    def _draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint) -> None:
        dx = end.x() - start.x()
        dy = end.y() - start.y()

        length = (dx * dx + dy * dy) ** 0.5

        if length == 0:
            return

        ux = dx / length
        uy = dy / length

        start_offset = 25
        end_offset = 25

        line_start = QPoint(
            int(start.x() + ux * start_offset),
            int(start.y() + uy * start_offset),
        )
        line_end = QPoint(
            int(end.x() - ux * end_offset),
            int(end.y() - uy * end_offset),
        )

        painter.drawLine(line_start, line_end)

        arrow_size = 10

        px = -uy
        py = ux

        tip = line_end
        left = QPoint(
            int(tip.x() - ux * arrow_size + px * arrow_size * 0.6),
            int(tip.y() - uy * arrow_size + py * arrow_size * 0.6),
        )
        right = QPoint(
            int(tip.x() - ux * arrow_size - px * arrow_size * 0.6),
            int(tip.y() - uy * arrow_size - py * arrow_size * 0.6),
        )

        painter.drawPolygon(QPolygon([tip, left, right]))
