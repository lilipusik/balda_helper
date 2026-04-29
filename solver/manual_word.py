from __future__ import annotations

from solver.board import Board, Cell
from solver.dictionary import normalize_word
from solver.hints import SuggestedMove


def find_manual_word_moves(
    *,
    board: Board,
    word: str,
    placed_row: int,
    placed_col: int,
    diagonals: bool,
) -> list[SuggestedMove]:
    word = normalize_word(word)

    if not word:
        return []

    if not board.is_inside(placed_row, placed_col):
        return []

    if board.get(placed_row, placed_col):
        return []

    neighbors_cache = board.build_neighbors_cache(diagonals)

    results: list[SuggestedMove] = []

    placed_key = (placed_row, placed_col)

    for start_row, start_col, _cell_value in board.iter_cells():
        _dfs_word(
            board=board,
            word=word,
            index=0,
            row=start_row,
            col=start_col,
            placed_key=placed_key,
            placed_letter=None,
            used=set(),
            path=[],
            results=results,
            neighbors_cache=neighbors_cache,
        )

    # Убираем полные дубли: одно и то же слово, та же буква, та же клетка, тот же путь.
    unique: dict[tuple[str, str, int, int, tuple[tuple[int, int], ...]], SuggestedMove] = {}

    for move in results:
        key = (
            move.word,
            move.letter,
            move.placed_cell.row,
            move.placed_cell.col,
            tuple((cell.row, cell.col) for cell in move.path),
        )
        unique[key] = move

    return list(unique.values())


def _dfs_word(
    *,
    board: Board,
    word: str,
    index: int,
    row: int,
    col: int,
    placed_key: tuple[int, int],
    placed_letter: str | None,
    used: set[tuple[int, int]],
    path: list[Cell],
    results: list[SuggestedMove],
    neighbors_cache: dict[tuple[int, int], tuple[Cell, ...]],
) -> None:
    key = (row, col)

    if key in used:
        return

    expected_letter = word[index]

    is_placed_cell = key == placed_key

    if is_placed_cell:
        if placed_letter is not None:
            return

        current_letter = expected_letter
        next_placed_letter = expected_letter
    else:
        current_letter = board.get(row, col)

        if current_letter != expected_letter:
            return

        next_placed_letter = placed_letter

    used.add(key)
    path.append(Cell(row, col))

    if index == len(word) - 1:
        if next_placed_letter is not None:
            results.append(
                SuggestedMove(
                    placed_cell=Cell(placed_key[0], placed_key[1]),
                    letter=next_placed_letter,
                    word=word,
                    path=tuple(path),
                    score=len(word),
                )
            )

        path.pop()
        used.remove(key)
        return

    for next_cell in neighbors_cache[(row, col)]:
        _dfs_word(
            board=board,
            word=word,
            index=index + 1,
            row=next_cell.row,
            col=next_cell.col,
            placed_key=placed_key,
            placed_letter=next_placed_letter,
            used=used,
            path=path,
            results=results,
            neighbors_cache=neighbors_cache,
        )

    path.pop()
    used.remove(key)