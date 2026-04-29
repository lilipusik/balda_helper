from __future__ import annotations

from dataclasses import dataclass

from solver.board import Board, Cell
from solver.dictionary import BaldaDictionary, normalize_word
from solver.trie import TrieNode

RUSSIAN_ALPHABET = "абвгдежзийклмнопрстуфхцчшщъыьэюя"

@dataclass(frozen=True, slots=True)
class SuggestedMove:
    placed_cell: Cell
    letter: str
    word: str
    path: tuple[Cell, ...]
    score: int

    @property
    def length(self) -> int:
        return len(self.word)


class BaldaHintSolver:
    __slots__ = ("dictionary",)

    def __init__(self, dictionary: BaldaDictionary) -> None:
        self.dictionary = dictionary

    def find_best_moves(
        self,
        board: Board,
        *,
        diagonals: bool,
        min_length: int = 2,
        alphabet: str = RUSSIAN_ALPHABET,
        limit: int | None = 100,
        excluded_words: set[str] | None = None,
    ) -> list[SuggestedMove]:
        if excluded_words is None:
            excluded_words = set()
        else:
            excluded_words = {normalize_word(word) for word in excluded_words}

        neighbors_cache = board.build_neighbors_cache(diagonals)
        empty_cells = board.empty_cells()

        suggestions: dict[
            tuple[str, int, int, str],
            SuggestedMove,
        ] = {}

        for placed_cell in empty_cells:
            for letter in alphabet:
                letter = normalize_word(letter)

                if len(letter) != 1:
                    continue

                self._find_moves_for_virtual_letter(
                    board=board,
                    placed_cell=placed_cell,
                    letter=letter,
                    neighbors_cache=neighbors_cache,
                    min_length=min_length,
                    excluded_words=excluded_words,
                    suggestions=suggestions,
                )

        result = list(suggestions.values())

        result.sort(
            key=lambda move: (
                -move.length,
                move.word,
                move.placed_cell.row,
                move.placed_cell.col,
                move.letter,
            )
        )

        return result

    def _find_moves_for_virtual_letter(
        self,
        *,
        board: Board,
        placed_cell: Cell,
        letter: str,
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
        min_length: int,
        excluded_words: set[str],
        suggestions: dict[tuple[str, int, int, str], SuggestedMove],
    ) -> None:
        for row, col, current_letter in board.iter_cells():
            is_placed_cell = (
                row == placed_cell.row
                and col == placed_cell.col
            )

            if is_placed_cell:
                start_letter = letter
            else:
                start_letter = current_letter

            if not start_letter:
                continue

            start_node = self.dictionary.trie.step(
                self.dictionary.trie.root,
                start_letter,
            )

            if start_node is None:
                continue

            start_cell = Cell(row, col)

            self._dfs(
                board=board,
                current_cell=start_cell,
                placed_cell=placed_cell,
                virtual_letter=letter,
                node=start_node,
                current_word=start_letter,
                path=[start_cell],
                used={(row, col)},
                used_placed_cell=is_placed_cell,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
                excluded_words=excluded_words,
                suggestions=suggestions,
            )

    def _dfs(
        self,
        *,
        board: Board,
        current_cell: Cell,
        placed_cell: Cell,
        virtual_letter: str,
        node: TrieNode,
        current_word: str,
        path: list[Cell],
        used: set[tuple[int, int]],
        used_placed_cell: bool,
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
        min_length: int,
        excluded_words: set[str],
        suggestions: dict[tuple[str, int, int, str], SuggestedMove],
    ) -> None:
        if len(current_word) > self.dictionary.max_word_length:
            return

        if (
            node.is_word
            and used_placed_cell
            and len(current_word) >= min_length
            and current_word not in excluded_words
        ):
            move = SuggestedMove(
                placed_cell=placed_cell,
                letter=virtual_letter,
                word=current_word,
                path=tuple(path),
                score=self._score_word(current_word),
            )

            # Вариант постановки считается уникальным по:
            # слово + строка + колонка + буква.
            #
            # Если одно и то же слово через ту же новую букву можно прочитать
            # несколькими путями, оставляем первый путь.
            # Для интерфейса это обычно правильно: пользователю важнее,
            # куда поставить букву.
            key = (
                current_word,
                placed_cell.row,
                placed_cell.col,
                virtual_letter,
            )

            old_move = suggestions.get(key)

            if old_move is None or move.score > old_move.score:
                suggestions[key] = move

        for next_cell in neighbors_cache[(current_cell.row, current_cell.col)]:
            key = (next_cell.row, next_cell.col)

            if key in used:
                continue

            is_placed_cell = (
                next_cell.row == placed_cell.row
                and next_cell.col == placed_cell.col
            )

            if is_placed_cell:
                next_letter = virtual_letter
            else:
                next_letter = board.get(next_cell.row, next_cell.col)

            # Нельзя ходить по другим пустым клеткам.
            if not next_letter:
                continue

            next_node = self.dictionary.trie.step(node, next_letter)

            if next_node is None:
                continue

            used.add(key)
            path.append(next_cell)

            self._dfs(
                board=board,
                current_cell=next_cell,
                placed_cell=placed_cell,
                virtual_letter=virtual_letter,
                node=next_node,
                current_word=current_word + next_letter,
                path=path,
                used=used,
                used_placed_cell=used_placed_cell or is_placed_cell,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
                excluded_words=excluded_words,
                suggestions=suggestions,
            )

            path.pop()
            used.remove(key)

    @staticmethod
    def _score_word(word: str) -> int:
        return len(word)