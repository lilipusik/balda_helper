import json
import re
from pathlib import Path
import pymorphy3

OUTPUT_FILE = Path("balda_nouns.json")
RUSSIAN_WORD_RE = re.compile(r"^[а-яе]+$")

BAD_GRAMMEMES = {
    "Name",  # имя
    "Surn",  # фамилия
    "Patr",  # отчество
    "Geox",  # географическое название
    "Orgn",  # организация
    "Trad",  # торговая марка
    "Abbr",  # аббревиатура
    "Init",  # инициалы
}

def normalize_word(word: str) -> str:
    return word.strip().lower().replace("ё", "е")


def is_clean_russian_word(word: str) -> bool:
    return bool(RUSSIAN_WORD_RE.fullmatch(word))


def has_bad_grammemes(tag) -> bool:
    return bool(BAD_GRAMMEMES & set(tag.grammemes))


def is_valid_balda_noun(word: str, tag, normal_form: str) -> bool:
    word = normalize_word(word)
    normal_form = normalize_word(normal_form)
    return not(not word or not is_clean_russian_word(word) or "NOUN" not in tag or has_bad_grammemes(tag) or word != normal_form)


def build_dictionary() -> list[str]:
    morph = pymorphy3.MorphAnalyzer(lang="ru")

    words: set[str] = set()

    for word, tag, normal_form, _para_id, _idx in morph.dictionary.iter_known_words():
        clean_word = normalize_word(word)

        if is_valid_balda_noun(clean_word, tag, normal_form):
            words.add(clean_word)

    return sorted(words)


def save_dictionary(words: list[str], output_file: Path) -> None:
    data = {
        "description": "Словарь существительных для игры Балда. Буква ё заменена на е.",
        "rules": {
            "part_of_speech": "NOUN",
            "only_normal_form": True,
            "yo_replaced_with_e": True,
            "excluded_grammemes": sorted(BAD_GRAMMEMES),
        },
        "count": len(words),
        "words": words,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("Собираю словарь существительных...")

    words = build_dictionary()

    save_dictionary(words, OUTPUT_FILE)

    print(f"Готово.")
    print(f"Файл: {OUTPUT_FILE.resolve()}")
    print(f"Слов сохранено: {len(words)}")


if __name__ == "__main__":
    main()