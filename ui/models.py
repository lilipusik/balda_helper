from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsedWordEntry:
    word: str
    row: int | None = None
    col: int | None = None
    letter: str | None = None