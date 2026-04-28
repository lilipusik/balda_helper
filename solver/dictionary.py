from __future__ import annotations

import json
from pathlib import Path

from solver.trie import Trie


class BaldaDictionary:
    __slots__ = ("words", "trie", "reverse_trie", "max_word_length")

    def __init__(self, words: set[str]) -> None:
        self.words = words
        self.max_word_length = max((len(word) for word in words), default=0)

        self.trie = Trie()
        self.trie.build_from_words(words)

        self.reverse_trie = Trie()
        self.reverse_trie.build_from_words({word[::-1] for word in words})

    @classmethod
    def from_json(cls, path: str | Path) -> "BaldaDictionary":
        path = Path(path)

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        raw_words = data["words"]

        words = {
            normalize_word(word)
            for word in raw_words
            if isinstance(word, str) and word
        }

        return cls(words)

    def contains(self, word: str) -> bool:
        return normalize_word(word) in self.words

    def has_prefix(self, prefix: str) -> bool:
        return self.trie.has_prefix(normalize_word(prefix))


def normalize_word(word: str) -> str:
    return word.strip().lower().replace("ё", "е")