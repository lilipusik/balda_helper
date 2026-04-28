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


@dataclass(frozen=True, slots=True)
class _LeftPart:
    text_before: str
    path_before: tuple[Cell, ...]
    used_keys: frozenset[tuple[int, int]]


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

        suggestions: dict[tuple[int, int, str, str], SuggestedMove] = {}

        if excluded_words is None:
            excluded_words = set()
        else:
            excluded_words = {normalize_word(word) for word in excluded_words}

        empty_cells = board.empty_cells()
        neighbors_cache = board.build_neighbors_cache(diagonals)

        for placed_cell in empty_cells:
            for letter in alphabet:
                letter = normalize_word(letter)

                if len(letter) != 1:
                    continue

                moves = self._find_moves_for_letter(
                    board=board,
                    placed_cell=placed_cell,
                    letter=letter,
                    neighbors_cache=neighbors_cache,
                    min_length=min_length,
                )

                for move in moves:
                    if move.word in excluded_words:
                        continue

                    key = (
                        move.placed_cell.row,
                        move.placed_cell.col,
                        move.letter,
                        move.word,
                    )

                    old_move = suggestions.get(key)

                    if old_move is None or move.score > old_move.score:
                        suggestions[key] = move

        result = list(suggestions.values())

        result.sort(
            key=lambda move: (
                -move.score,
                -move.length,
                move.word,
                move.placed_cell.row,
                move.placed_cell.col,
                move.letter,
            )
        )

        if limit is not None:
            result = result[:limit]

        return result

    def _find_moves_for_letter(
        self,
        *,
        board: Board,
        placed_cell: Cell,
        letter: str,
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
        min_length: int,
    ) -> list[SuggestedMove]:
        found: dict[str, SuggestedMove] = {}

        reverse_start_node = self.dictionary.reverse_trie.step(
            self.dictionary.reverse_trie.root,
            letter,
        )

        if reverse_start_node is None:
            return []

        left_parts = self._collect_left_parts(
            board=board,
            placed_cell=placed_cell,
            letter=letter,
            reverse_node=reverse_start_node,
            neighbors_cache=neighbors_cache,
        )

        for left_part in left_parts:
            prefix = left_part.text_before + letter

            forward_node = self.dictionary.trie.follow(prefix)

            if forward_node is None:
                continue

            start_path = left_part.path_before + (placed_cell,)
            used = set(left_part.used_keys)

            self._extend_right(
                board=board,
                current_cell=placed_cell,
                placed_cell=placed_cell,
                letter=letter,
                node=forward_node,
                current_word=prefix,
                path=start_path,
                used=used,
                found=found,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
            )

        return list(found.values())

    def _collect_left_parts(
        self,
        *,
        board: Board,
        placed_cell: Cell,
        letter: str,
        reverse_node: TrieNode,
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
    ) -> list[_LeftPart]:
        result: list[_LeftPart] = []

        placed_key = (placed_cell.row, placed_cell.col)

        start_part = _LeftPart(
            text_before="",
            path_before=(),
            used_keys=frozenset({placed_key}),
        )

        result.append(start_part)

        self._dfs_left(
            board=board,
            current_cell=placed_cell,
            reverse_node=reverse_node,
            text_before="",
            path_before=(),
            used={placed_key},
            result=result,
            neighbors_cache=neighbors_cache,
        )

        return result

    def _dfs_left(
        self,
        *,
        board: Board,
        current_cell: Cell,
        reverse_node: TrieNode,
        text_before: str,
        path_before: tuple[Cell, ...],
        used: set[tuple[int, int]],
        result: list[_LeftPart],
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
    ) -> None:
        # +1 потому что поставленная буква уже есть в слове.
        if len(text_before) + 1 >= self.dictionary.max_word_length:
            return

        for previous_cell in neighbors_cache[(current_cell.row, current_cell.col)]:
            key = (previous_cell.row, previous_cell.col)

            if key in used:
                continue

            previous_letter = board.get(previous_cell.row, previous_cell.col)

            # Влево от новой буквы можно идти только по уже существующим буквам.
            if not previous_letter:
                continue

            next_reverse_node = self.dictionary.reverse_trie.step(
                reverse_node,
                previous_letter,
            )

            if next_reverse_node is None:
                continue

            used.add(key)

            new_text_before = previous_letter + text_before
            new_path_before = (previous_cell,) + path_before

            result.append(
                _LeftPart(
                    text_before=new_text_before,
                    path_before=new_path_before,
                    used_keys=frozenset(used),
                )
            )

            self._dfs_left(
                board=board,
                current_cell=previous_cell,
                reverse_node=next_reverse_node,
                text_before=new_text_before,
                path_before=new_path_before,
                used=used,
                result=result,
                neighbors_cache=neighbors_cache,
            )

            used.remove(key)

    def _extend_right(
        self,
        *,
        board: Board,
        current_cell: Cell,
        placed_cell: Cell,
        letter: str,
        node: TrieNode,
        current_word: str,
        path: tuple[Cell, ...],
        used: set[tuple[int, int]],
        found: dict[str, SuggestedMove],
        neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
        min_length: int,
    ) -> None:
        if len(current_word) > self.dictionary.max_word_length:
            return

        if node.is_word and len(current_word) >= min_length:
            score = self._score_word(current_word)

            move = SuggestedMove(
                placed_cell=placed_cell,
                letter=letter,
                word=current_word,
                path=path,
                score=score,
            )

            old_move = found.get(current_word)

            if old_move is None or move.score > old_move.score:
                found[current_word] = move

        for next_cell in neighbors_cache[(current_cell.row, current_cell.col)]:
            key = (next_cell.row, next_cell.col)

            if key in used:
                continue

            next_letter = board.get(next_cell.row, next_cell.col)

            # Справа от новой буквы тоже можно идти только по уже существующим буквам.
            if not next_letter:
                continue

            next_node = self.dictionary.trie.step(node, next_letter)

            if next_node is None:
                continue

            used.add(key)

            self._extend_right(
                board=board,
                current_cell=next_cell,
                placed_cell=placed_cell,
                letter=letter,
                node=next_node,
                current_word=current_word + next_letter,
                path=path + (next_cell,),
                used=used,
                found=found,
                neighbors_cache=neighbors_cache,
                min_length=min_length,
            )

            used.remove(key)

    @staticmethod
    def _score_word(word: str) -> int:
        return len(word)