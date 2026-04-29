from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from solver.board import Board
from solver.dictionary import BaldaDictionary
from solver.hints import BaldaHintSolver
from services.definitions import DefinitionService


class SolverThread(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        *,
        dictionary: BaldaDictionary,
        grid: list[list[str]],
        diagonals: bool,
        min_length: int,
        limit: int | None,
        excluded_words: set[str],
    ) -> None:
        super().__init__()

        self.dictionary = dictionary
        self.grid = grid
        self.diagonals = diagonals
        self.min_length = min_length
        self.limit = limit
        self.excluded_words = excluded_words

    def run(self) -> None:
        try:
            board = Board(self.grid)
            solver = BaldaHintSolver(self.dictionary)

            moves = solver.find_best_moves(
                board,
                diagonals=self.diagonals,
                min_length=self.min_length,
                limit=self.limit,
                excluded_words=self.excluded_words,
            )

            self.finished_ok.emit(moves)

        except Exception as error:
            self.failed.emit(str(error))


class DefinitionThread(QThread):
    finished_ok = Signal(object)

    def __init__(
        self,
        *,
        service: DefinitionService,
        word: str,
    ) -> None:
        super().__init__()

        self.service = service
        self.word = word

    def run(self) -> None:
        result = self.service.get_definition(self.word)
        self.finished_ok.emit(result)