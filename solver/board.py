from __future__ import annotations
from dataclasses import dataclass
from solver.dictionary import normalize_word

@dataclass(frozen=True, slots=True)
class Cell:
    row: int
    col: int

class Board:
    __slots__ = ("grid", "rows", "cols")

    def __init__(self, grid: list[list[str]] | tuple[tuple[str, ...], ...]) -> None:
        if not grid:
            raise ValueError("Поле не может быть пустым")

        rows = len(grid)
        cols = len(grid[0])

        if cols == 0:
            raise ValueError("Поле не может иметь пустые строки")

        normalized_grid: list[tuple[str, ...]] = []

        for row in grid:
            if len(row) != cols:
                raise ValueError("Все строки поля должны быть одной длины")

            normalized_row = tuple(self._normalize_cell(value) for value in row)
            normalized_grid.append(normalized_row)

        self.grid = tuple(normalized_grid)
        self.rows = rows
        self.cols = cols

    @staticmethod
    def _normalize_cell(value: str) -> str:
        value = normalize_word(value)

        if value == "":
            return ""

        if len(value) != 1:
            raise ValueError(f"В клетке должна быть одна буква, получено: {value!r}")

        if not ("а" <= value <= "я"):
            raise ValueError(f"Разрешены только русские буквы, получено: {value!r}")

        return value

    def get(self, row: int, col: int) -> str:
        return self.grid[row][col]

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def iter_cells(self):
        for row in range(self.rows):
            for col in range(self.cols):
                yield row, col, self.grid[row][col]

    def iter_positions(self):
        for row in range(self.rows):
            for col in range(self.cols):
                yield row, col

    def empty_cells(self) -> list[Cell]:
        result: list[Cell] = []

        for row, col, value in self.iter_cells():
            if value == "":
                result.append(Cell(row, col))

        return result

    def with_letter(self, row: int, col: int, letter: str) -> "Board":
        letter = self._normalize_cell(letter)

        if self.grid[row][col] != "":
            raise ValueError("Нельзя поставить букву в непустую клетку")

        new_grid = [list(row_values) for row_values in self.grid]
        new_grid[row][col] = letter

        return Board(new_grid)

    def build_neighbors_cache(self, diagonals: bool) -> dict[tuple[int, int], tuple[Cell, ...]]:
        if diagonals:
            directions = (
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1),
            )
        else:
            directions = (
                (-1, 0),
                (0, -1),  (0, 1),
                (1, 0),
            )

        cache: dict[tuple[int, int], tuple[Cell, ...]] = {}

        for row, col in self.iter_positions():
            neighbors: list[Cell] = []

            for dr, dc in directions:
                next_row = row + dr
                next_col = col + dc

                if self.is_inside(next_row, next_col):
                    neighbors.append(Cell(next_row, next_col))

            cache[(row, col)] = tuple(neighbors)

        return cache

    def __str__(self) -> str:
        lines = []

        for row in self.grid:
            line = " ".join(cell if cell else "." for cell in row)
            lines.append(line)

        return "\n".join(lines)