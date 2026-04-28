from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    is_word: bool = False


class Trie:
    __slots__ = ("root",)

    def __init__(self) -> None:
        self.root = TrieNode()

    def add(self, word: str) -> None:
        node = self.root

        for char in word:
            next_node = node.children.get(char)

            if next_node is None:
                next_node = TrieNode()
                node.children[char] = next_node

            node = next_node

        node.is_word = True

    def build_from_words(self, words: list[str] | set[str]) -> None:
        for word in words:
            self.add(word)

    def contains(self, word: str) -> bool:
        node = self.follow(word)
        return node is not None and node.is_word

    def has_prefix(self, prefix: str) -> bool:
        return self.follow(prefix) is not None

    def follow(self, text: str) -> TrieNode | None:
        node = self.root

        for char in text:
            node = node.children.get(char)
            if node is None:
                return None

        return node

    @staticmethod
    def step(node: TrieNode, char: str) -> TrieNode | None:
        return node.children.get(char)