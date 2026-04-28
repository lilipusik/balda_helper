from __future__ import annotations
from dataclasses import dataclass
from solver.board import Board, Cell
from solver.dictionary import BaldaDictionary
from solver.trie import TrieNode

@dataclass(frozen=True, slots=True)
class FoundWord:
    word: str
    path: tuple[Cell, ...]

    @property
    def length(self) -> int:
        return len(self.word)


class BaldaSolver:
    __slots__ = ("dictionary",)

    def __init__(self, dictionary: BaldaDictionary) -> None:
        self.dictionary = dictionary

    def find_words_on_board(
        self,
        board: Board,
        *,
        diagonals: bool,
        min_length: int = 2,
    ) -> list[FoundWord]:
        found: dict[str, FoundWord] = {}
        neighbors_cache = board.build_neighbors_cache(diagonals)

        for row, col, letter in board.iter_cells():
            if not letter:
                continue

            start_node = self.dictionary.trie.step(
                self.dictionary.trie.root,
                letter,
            )

            if start_node is None:
                continue

            start_cell = Cell(row, col)

            self._dfs(
                board=board,
                row=row,
                col=col,
                node=start_node,
                current_word=letter,
                path=(start_cell,),
                used={(row, col)},
                found=found,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
            )

        result = list(found.values())

        result.sort(
            key=lambda item: (
                -item.length,
                item.word,
            )
        )

        return result

    def _dfs(
        self,
        *,
        board: Board,
        row: int,
        col: int,
        node: TrieNode,
        current_word: str,
        path: tuple[Cell, ...],
        used: set[tuple[int, int]],
        found: dict[str, FoundWord],
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
        min_length: int,
    ) -> None:
        if len(current_word) > self.dictionary.max_word_length:
            return

        if node.is_word and len(current_word) >= min_length:
            found.setdefault(
                current_word,
                FoundWord(
                    word=current_word,
                    path=path,
                ),
            )

        for next_cell in neighbors_cache[(row, col)]:
            key = (next_cell.row, next_cell.col)

            if key in used:
                continue

            next_letter = board.get(next_cell.row, next_cell.col)

            if not next_letter:
                continue

            next_node = self.dictionary.trie.step(node, next_letter)

            if next_node is None:
                continue

            used.add(key)

            self._dfs(
                board=board,
                row=next_cell.row,
                col=next_cell.col,
                node=next_node,
                current_word=current_word + next_letter,
                path=path + (next_cell,),
                used=used,
                found=found,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
            )

            used.remove(key)