from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass


RU_WIKTIONARY_API = "https://ru.wiktionary.org/w/api.php"


@dataclass(frozen=True, slots=True)
class DefinitionResult:
    word: str
    definition: str | None
    source: str | None = None


class DefinitionService:
    def __init__(self) -> None:
        self._cache: dict[str, DefinitionResult] = {}

    def get_definition(self, word: str) -> DefinitionResult:
        word = self._normalize_word(word)

        if not word:
            return DefinitionResult(word=word, definition=None, source=None)

        cached = self._cache.get(word)

        if cached is not None:
            return cached

        result = self._fetch_from_wiktionary(word)
        self._cache[word] = result

        return result

    def _fetch_from_wiktionary(self, word: str) -> DefinitionResult:
        try:
            page_text = self._load_wiktionary_page_text(word)
        except Exception:
            return DefinitionResult(
                word=word,
                definition=None,
                source="ru.wiktionary.org",
            )

        if not page_text:
            return DefinitionResult(
                word=word,
                definition=None,
                source="ru.wiktionary.org",
            )

        definition = self._extract_definition_from_wikitext(page_text)

        return DefinitionResult(
            word=word,
            definition=definition,
            source="ru.wiktionary.org",
        )

    def _load_wiktionary_page_text(self, word: str) -> str | None:
        query = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": word,
            "rvprop": "content",
            "rvslots": "main",
            "formatversion": "2",
            "redirects": "1",
        }

        url = RU_WIKTIONARY_API + "?" + urllib.parse.urlencode(query)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "BaldaHelper/1.0 definition lookup",
            },
        )

        with urllib.request.urlopen(request, timeout=6) as response:
            raw_data = response.read().decode("utf-8")

        data = json.loads(raw_data)

        pages = data.get("query", {}).get("pages", [])

        if not pages:
            return None

        page = pages[0]

        if page.get("missing"):
            return None

        revisions = page.get("revisions", [])

        if not revisions:
            return None

        slots = revisions[0].get("slots", {})
        main_slot = slots.get("main", {})

        return main_slot.get("content")

    def _extract_definition_from_wikitext(self, text: str) -> str | None:
        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line.startswith("#"):
                continue

            # Пропускаем примеры, цитаты, переводы и вложенные пункты.
            if line.startswith("#*") or line.startswith("#:") or line.startswith("##"):
                continue

            line = line.lstrip("#").strip()

            if not line:
                continue

            line = self._clean_wikitext(line)

            if not line:
                continue

            if len(line) > 300:
                line = line[:297].rstrip() + "..."

            return line

        return None

    def _clean_wikitext(self, text: str) -> str:
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)

        # [[слово|текст]] -> текст
        text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)

        # [[слово]] -> слово
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)

        # [https://example.com текст] -> текст
        text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)

        # Убираем оставшиеся HTML-теги.
        text = re.sub(r"<[^>]+>", "", text)

        # Убираем служебные остатки.
        text = text.replace("'''", "")
        text = text.replace("''", "")
        text = text.replace("&nbsp;", " ")

        text = re.sub(r"\s+", " ", text)

        return text.strip(" ;,.—–-")

    def _normalize_word(self, word: str) -> str:
        return word.strip().lower().replace("ё", "е")