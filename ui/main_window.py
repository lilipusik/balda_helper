from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QInputDialog,
)

from solver.board import Board
from solver.dictionary import BaldaDictionary, normalize_word
from solver.hints import BaldaHintSolver, SuggestedMove
from solver.manual_word import find_manual_word_moves
from services.definitions import DefinitionService, DefinitionResult

from ui.models import UsedWordEntry
from ui.threads import SolverThread, DefinitionThread
from ui.styles import APP_STYLE
from ui.widgets.board_widget import BoardWidget
from ui.widgets.definition_popup import DefinitionPopup
from ui.widgets.hints_tree import HoverTreeWidget
from ui.widgets.used_words_cloud import UsedWordsCloud
from utils.resources import resource_path


DICTIONARY_PATH = resource_path("data/balda_nouns.json")

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.dictionary: BaldaDictionary | None = None
        self.current_moves: list[SuggestedMove] = []
        self.used_words: dict[str, UsedWordEntry] = {}
        self.hidden_hint_words: set[str] = set()
        self.solver_thread: SolverThread | None = None
        self.preview_base_grid: list[list[str]] | None = None
        self.pending_external_word: str | None = None
        self.pending_external_word_is_custom: bool = False
        self.letter_frequency_score: dict[str, float] = {}
        self.definition_service = DefinitionService()
        self.definition_thread: DefinitionThread | None = None
        self.definition_tooltip_cache: dict[str, str] = {}

        self.definition_popup = DefinitionPopup()
        self.definition_popup_word: str | None = None

        self.start_word_timer = QTimer(self)
        self.start_word_timer.setSingleShot(True)
        self.start_word_timer.setInterval(700)
        self.start_word_timer.timeout.connect(self._auto_add_horizontal_words)

        self.setWindowTitle("Подсказчик для Балды")
        self.resize(1220, 740)

        self._build_ui()
        self._apply_app_style()
        self._load_dictionary()
        self._rebuild_board()

    def _used_words_set(self) -> set[str]:
        return set(self.used_words.keys())

    def _remove_word_from_current_hints(self, word: str) -> None:
        word = normalize_word(word)

        self.current_moves = [
            move
            for move in self.current_moves
            if normalize_word(move.word) != word
        ]

        self._refresh_results_table()

    def _add_external_word(self) -> None:
        if self.dictionary is None:
            QMessageBox.warning(self, "Нет словаря", "Словарь не загружен.")
            return

        while True:
            text, ok = QInputDialog.getText(
                self,
                "Добавить новое слово",
                "Введите слово другого игрока:",
            )

            if not ok:
                return

            word = normalize_word(text)

            if not word:
                return

            if word in self.used_words:
                QMessageBox.information(
                    self,
                    "Слово уже использовано",
                    f"Слово «{word}» уже есть в использованных.",
                )
                return

            if len(word) < self.min_length_spin.value():
                QMessageBox.warning(
                    self,
                    "Слишком короткое слово",
                    f"Минимальная длина слова: {self.min_length_spin.value()}",
                )
                continue

            is_custom_word = False

            if not self.dictionary.contains(word):
                reply = QMessageBox.question(
                    self,
                    "Слово не найдено",
                    f"Слово «{word}» не найдено в словаре.\n\n"
                    f"Вы уверены, что оно правильное?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.No:
                    continue

                self._add_word_to_runtime_dictionary(word)
                is_custom_word = True

            self.pending_external_word = word
            self.pending_external_word_is_custom = is_custom_word

            self._clear_highlight()

            self.status_label.setText(
                f"Выберите пустую клетку для слова «{word}»."
            )

            return
        
    def _ask_manual_letter_for_external_word(self, word: str) -> str | None:
        while True:
            text, ok = QInputDialog.getText(
                self,
                "Укажите букву",
                f"Какую букву поставить для слова «{word}»?",
            )

            if not ok:
                return None

            letter = normalize_word(text)

            if len(letter) != 1 or not ("а" <= letter <= "я"):
                QMessageBox.warning(
                    self,
                    "Некорректная буква",
                    "Введите одну русскую букву.",
                )
                continue

            if letter not in word:
                reply = QMessageBox.question(
                    self,
                    "Буквы нет в слове",
                    f"Буквы «{letter}» нет в слове «{word}».\n\n"
                    f"Все равно поставить эту букву?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.No:
                    continue

            return letter
        
    def _apply_manual_external_word(
        self,
        *,
        word: str,
        row: int,
        col: int,
        letter: str,
    ) -> None:
        word = normalize_word(word)
        letter = normalize_word(letter)

        if self.preview_base_grid is not None:
            self.board_widget.restore_grid(self.preview_base_grid)
            self.preview_base_grid = None
        else:
            self.board_widget.clear_highlight()

        cell = self.board_widget.cells[row][col]
        cell.set_value_silent(letter)
        cell.set_normal_style()
        cell.setToolTip("")

        self.used_words[word] = UsedWordEntry(
            word=word,
            row=row,
            col=col,
            letter=letter,
        )
        self._refresh_used_words_list()

        self.pending_external_word = None
        self.pending_external_word_is_custom = False

        self.current_moves = []
        self.results_tree.clear()

        self.status_label.setText(
            f"Слово «{word}» добавлено. Буква «{letter}» поставлена."
        )

        self._start_search()

    def _on_board_cell_clicked(self, row: int, col: int) -> None:
        if self.pending_external_word is None:
            return

        word = self.pending_external_word

        current_value = self.board_widget.cells[row][col].value()

        if current_value:
            QMessageBox.information(
                self,
                "Клетка занята",
                "Для нового слова нужно выбрать пустую клетку.",
            )
            return

        matching_moves = self._find_manual_moves_for_word_at_cell(word, row, col)

        if not matching_moves:
            reply = QMessageBox.question(
                self,
                "Не удалось определить букву",
                f"Я не смог автоматически найти путь для слова «{word}» "
                f"с новой буквой в клетке ({row + 1}, {col + 1}).\n\n"
                f"Хотите указать букву вручную?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.No:
                return

            letter = self._ask_manual_letter_for_external_word(word)

            if letter is None:
                return

            self._apply_manual_external_word(
                word=word,
                row=row,
                col=col,
                letter=letter,
            )
            return

        matching_moves.sort(
            key=lambda move: (
                move.letter,
                move.word,
                move.placed_cell.row,
                move.placed_cell.col,
            )
        )

        move = matching_moves[0]

        self.pending_external_word = None
        self.pending_external_word_is_custom = False
        self._apply_used_move(move)

    def _find_manual_moves_for_word_at_cell(
        self,
        word: str,
        row: int,
        col: int,
    ) -> list[SuggestedMove]:
        grid = self.board_widget.grid_values()
        board = Board(grid)

        return find_manual_word_moves(
            board=board,
            word=word,
            placed_row=row,
            placed_col=col,
            diagonals=self.diagonal_checkbox.isChecked(),
        )
    
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(22, 22, 22, 22)
        left_layout.setSpacing(18)

        title = QLabel("Балда Helper")
        title.setObjectName("title")

        subtitle = QLabel("Наведи курсор на слово — поле покажет путь чтения и новую букву.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(14)

        self.size_combo = QComboBox()
        for size in range(4, 11):
            self.size_combo.addItem(f"{size} × {size}", size)

        self.size_combo.setCurrentIndex(1)
        self.size_combo.currentIndexChanged.connect(self._rebuild_board)

        self.diagonal_checkbox = QCheckBox("Диагонали")
        self.diagonal_checkbox.setChecked(True)

        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(2, 20)
        self.min_length_spin.setValue(3)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 1000)
        self.limit_spin.setValue(100)
        self.limit_spin.setSingleStep(10)

        settings_row.addWidget(self._labeled_widget("Размер", self.size_combo))
        settings_row.addWidget(self._labeled_widget("Мин. длина", self.min_length_spin))
        settings_row.addWidget(self._labeled_widget("Лимит", self.limit_spin))
        settings_row.addWidget(self.diagonal_checkbox)
        settings_row.addStretch()

        left_layout.addLayout(settings_row)

        self.board_widget = BoardWidget()
        self.board_widget.board_edited.connect(self._schedule_start_word_scan)
        self.board_widget.cell_clicked.connect(self._on_board_cell_clicked)
        left_layout.addWidget(self.board_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        self.search_button = QPushButton("Найти подсказки")
        self.search_button.setObjectName("primaryButton")
        self.search_button.clicked.connect(self._start_search)

        self.clear_button = QPushButton("Новая игра")
        self.clear_button.clicked.connect(self._new_game)

        self.add_external_word_button = QPushButton("Добавить новое слово")
        self.add_external_word_button.clicked.connect(self._add_external_word)

        buttons_row.addWidget(self.search_button)
        buttons_row.addWidget(self.add_external_word_button)
        buttons_row.addWidget(self.clear_button)
        buttons_row.addStretch()

        left_layout.addLayout(buttons_row)

        self.status_label = QLabel("Готово.")
        self.status_label.setObjectName("status")
        left_layout.addWidget(self.status_label)

        right_panel = QFrame()
        right_panel.setObjectName("panel")

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(22, 22, 22, 22)
        right_layout.setSpacing(16)

        # -------------------------
        # Верх: найденные подсказки
        # -------------------------

        moves_section = QFrame()
        moves_section.setObjectName("innerPanel")
        moves_layout = QVBoxLayout(moves_section)
        moves_layout.setContentsMargins(0, 0, 0, 0)
        moves_layout.setSpacing(12)

        results_title = QLabel("Найденные подсказки")
        results_title.setObjectName("sectionTitle")

        self.results_tree = HoverTreeWidget()
        self.results_tree.setColumnCount(5)
        self.results_tree.setHeaderLabels(["Слово", "Букв", "Варианты", "?", "Убрать"])
        self.results_tree.setMouseTracking(True)
        self.results_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.results_tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.results_tree.setRootIsDecorated(True)
        self.results_tree.setUniformRowHeights(True)

        self.results_tree.header().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.results_tree.header().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.results_tree.header().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        self.results_tree.header().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.results_tree.header().setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.results_tree.itemEntered.connect(self._on_result_hovered)
        self.results_tree.itemClicked.connect(self._on_result_clicked)
        self.results_tree.mouse_left.connect(self._clear_highlight)

        moves_layout.addWidget(results_title)
        moves_layout.addWidget(self.results_tree, stretch=1)

        # -------------------------
        # Низ: использованные слова
        # -------------------------

        used_section = QFrame()
        used_section.setObjectName("innerPanel")
        used_layout = QVBoxLayout(used_section)
        used_layout.setContentsMargins(0, 0, 0, 0)
        used_layout.setSpacing(12)

        used_title = QLabel("Использованные слова")
        used_title.setObjectName("sectionTitle")

        self.used_words_cloud = UsedWordsCloud()
        self.used_words_cloud.word_clicked.connect(self._remove_used_word_by_text)

        self.used_words_scroll = QScrollArea()
        self.used_words_scroll.setWidgetResizable(True)
        self.used_words_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.used_words_scroll.setWidget(self.used_words_cloud)
        self.used_words_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.used_words_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        used_hint = QLabel("Кликните по слову, чтобы удалить его.")
        used_hint.setObjectName("smallLabel")

        used_layout.addWidget(used_title)
        used_layout.addWidget(self.used_words_scroll, stretch=1)
        used_layout.addWidget(used_hint)

        right_layout.addWidget(moves_section, stretch=5)
        right_layout.addWidget(used_section, stretch=2)

        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=2)

        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=3)

    def _ensure_definition_for_item(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()

        if parent is not None:
            item = parent

        word = normalize_word(item.text(0))

        if not word:
            return

        cached = self.definition_tooltip_cache.get(word)

        if cached is not None:
            item.setToolTip(3, cached)
            return

        if self.definition_thread is not None:
            return

        item.setToolTip(3, "Загружаю определение...")

        self.definition_thread = DefinitionThread(
            service=self.definition_service,
            word=word,
        )

        self.definition_thread.finished_ok.connect(self._on_definition_loaded)
        self.definition_thread.finished.connect(self._on_definition_thread_finished)
        self.definition_thread.start()

    def _on_definition_loaded(self, result: DefinitionResult) -> None:
        word = normalize_word(result.word)

        if result.definition:
            text = result.definition
        else:
            text = "Определение не найдено"

        self.definition_tooltip_cache[word] = text

        items = self.results_tree.findItems(
            word,
            Qt.MatchFlag.MatchExactly,
            0,
        )

        for item in items:
            item.setToolTip(3, text)

        if self.definition_popup_word == word and self.definition_popup.isVisible():
            self.definition_popup.show_definition(
                word=word,
                text=text,
                global_pos=self.cursor().pos(),
            )


    def _on_definition_thread_finished(self) -> None:
        self.definition_thread = None

    def _labeled_widget(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("smallLabel")

        layout.addWidget(label)
        layout.addWidget(widget)

        return container

    def _apply_app_style(self) -> None:
        self.setStyleSheet(APP_STYLE)

    def _load_dictionary(self) -> None:
        if not DICTIONARY_PATH.exists():
            QMessageBox.critical(
                self,
                "Словарь не найден",
                f"Не найден файл словаря:\n{DICTIONARY_PATH}\n\n"
                f"Сначала создай data/balda_nouns.json.",
            )
            self.search_button.setEnabled(False)
            self.status_label.setText("Словарь не найден.")
            return

        try:
            self.status_label.setText("Загружаю словарь...")
            QApplication.processEvents()

            self.dictionary = BaldaDictionary.from_json(DICTIONARY_PATH)
            self.letter_frequency_score = self._build_letter_frequency_score(
                self.dictionary.words
            )

            self.status_label.setText(f"Словарь загружен: {len(self.dictionary.words)} слов.")

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка загрузки словаря",
                str(error),
            )
            self.search_button.setEnabled(False)
            self.status_label.setText("Ошибка загрузки словаря.")

    def _build_letter_frequency_score(self, words: set[str]) -> dict[str, float]:
        counts: dict[str, int] = {}
        total = 0

        for word in words:
            word = normalize_word(word)

            for letter in word:
                if "а" <= letter <= "я":
                    counts[letter] = counts.get(letter, 0) + 1
                    total += 1

        if total == 0:
            return {}

        return {
            letter: count / total
            for letter, count in counts.items()
        }

    def _letter_frequency_score(self, word: str) -> float:
        word = normalize_word(word)

        if not word:
            return 0.0

        return sum(
            self.letter_frequency_score.get(letter, 0.0)
            for letter in word
        )

    def _move_sort_key(self, move: SuggestedMove) -> tuple:
        word = normalize_word(move.word)

        return (
            -move.length,
            -self._letter_frequency_score(word),
            word,
            move.placed_cell.row,
            move.placed_cell.col,
            move.letter,
        )


    def _word_sort_key(self, word: str) -> tuple:
        word = normalize_word(word)

        return (
            -len(word),
            -self._letter_frequency_score(word),
            word,
        )

    def _rebuild_board(self) -> None:
        old_values = self.board_widget.grid_values() if hasattr(self, "board_widget") else []

        size = self.size_combo.currentData()
        self.board_widget.rebuild(size, old_values)

        self.preview_base_grid = None
        self.current_moves = []

        self.results_tree.clear()
        self.status_label.setText(f"Поле {size} × {size} готово.")

    def _new_game(self) -> None:
        self.board_widget.clear_values()

        self.preview_base_grid = None
        self.pending_external_word = None
        self.pending_external_word_is_custom = False
        self.current_moves = []
        self.used_words.clear()
        self.hidden_hint_words.clear()

        self.results_tree.clear()
        self.used_words_cloud.set_words([])

        self.status_label.setText("Поле и использованные слова очищены.")

    def _clear_highlight(self) -> None:
        self.definition_popup.hide_popup()

        if self.preview_base_grid is not None:
            self.board_widget.restore_grid(self.preview_base_grid)
            self.preview_base_grid = None
        else:
            self.board_widget.clear_highlight()

    def _show_definition_popup_for_item(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()

        if parent is not None:
            item = parent

        word = normalize_word(item.text(0))

        if not word:
            return

        self.definition_popup_word = word

        cached = self.definition_tooltip_cache.get(word)

        cursor_pos = self.results_tree.mapToGlobal(
            self.results_tree.viewport().mapFromGlobal(self.cursor().pos())
        )

        if cached is not None:
            self.definition_popup.show_definition(
                word=word,
                text=cached,
                global_pos=self.cursor().pos(),
            )
            return

        self.definition_popup.show_definition(
            word=word,
            text="Загружаю определение...",
            global_pos=self.cursor().pos(),
        )

        self._ensure_definition_for_item(item)

    def _schedule_start_word_scan(self) -> None:
        self.start_word_timer.start()

        self.current_moves = []
        self.results_tree.clear()

        if self.preview_base_grid is not None:
            self.preview_base_grid = None

        self.board_widget.clear_highlight()

    def _auto_add_horizontal_words(self) -> None:
        if self.dictionary is None:
            return

        grid = self.board_widget.grid_values()
        min_length = self.min_length_spin.value()

        added_words: list[str] = []

        for row in grid:
            current = ""

            for value in row + [""]:
                if value:
                    current += value
                    continue

                if len(current) >= min_length:
                    word = normalize_word(current)
                    
                    if (
                        word
                        and word not in self.used_words
                        and self.dictionary.contains(word)
                    ):
                        self.used_words[word] = UsedWordEntry(word=word)
                        added_words.append(word)

                current = ""

        if not added_words:
            return

        self._refresh_used_words_list()

        words_text = ", ".join(sorted(added_words))

        self.status_label.setText(
            f"Стартовое слово добавлено в использованные: {words_text}"
        )

    def _add_word_to_runtime_dictionary(self, word: str) -> None:
        """
        Добавляет слово в словарь текущей сессии.

        Важно:
        Это добавляет слово только в память приложения.
        В JSON-файл balda_nouns.json слово пока не сохраняется.
        """
        if self.dictionary is None:
            return

        word = normalize_word(word)

        if not word:
            return

        if word in self.dictionary.words:
            return

        self.dictionary.words.add(word)
        self.dictionary.max_word_length = max(self.dictionary.max_word_length, len(word))

        self.dictionary.trie.add(word)
        self.dictionary.reverse_trie.add(word[::-1])

    def _start_search(self) -> None:
        if self.dictionary is None:
            QMessageBox.warning(self, "Нет словаря", "Словарь не загружен.")
            return

        self._clear_highlight()

        grid = self.board_widget.grid_values()

        if not any(any(cell for cell in row) for row in grid):
            QMessageBox.information(
                self,
                "Пустое поле",
                "Введите хотя бы несколько букв на поле.",
            )
            return

        self.results_tree.clear()
        self.status_label.setText("Поиск...")
        self.search_button.setEnabled(False)

        self.solver_thread = SolverThread(
            dictionary=self.dictionary,
            grid=grid,
            diagonals=self.diagonal_checkbox.isChecked(),
            min_length=self.min_length_spin.value(),
            limit=None,
            excluded_words=self._used_words_set(),
        )

        self.solver_thread.finished_ok.connect(self._on_search_finished)
        self.solver_thread.failed.connect(self._on_search_failed)
        self.solver_thread.finished.connect(self._on_thread_finished)

        self.solver_thread.start()

    def _on_search_finished(self, moves: list[SuggestedMove]) -> None:
        moves = [
            move
            for move in moves
            if normalize_word(move.word) not in self.hidden_hint_words
        ]

        self.current_moves = sorted(
            moves,
            key=self._move_sort_key,
        )

        self._refresh_results_table()

        if not self.current_moves:
            self.status_label.setText("Подсказки не найдены.")
            return

        unique_words_count = len({
            normalize_word(move.word)
            for move in self.current_moves
        })

        self.status_label.setText(
            f"Найдено слов: {unique_words_count}. Вариантов ходов: {len(self.current_moves)}."
        )

    def _on_search_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Ошибка поиска",
            message,
        )

        self.status_label.setText("Ошибка поиска.")

    def _on_thread_finished(self) -> None:
        self.search_button.setEnabled(True)
        self.solver_thread = None

    def _refresh_results_table(self) -> None:
        self.current_moves = [
            move
            for move in self.current_moves
            if normalize_word(move.word) not in self.hidden_hint_words
        ]

        self.current_moves = sorted(
            self.current_moves,
            key=self._move_sort_key,
        )

        self.results_tree.clear()

        grouped: dict[str, list[SuggestedMove]] = {}

        for move in self.current_moves:
            word = normalize_word(move.word)
            grouped.setdefault(word, []).append(move)

        sorted_words = sorted(
            grouped.keys(),
            key=self._word_sort_key,
        )

        shown_words = sorted_words[: self.limit_spin.value()]

        move_index_by_id = {
            id(move): index
            for index, move in enumerate(self.current_moves)
        }

        for word_index, word in enumerate(shown_words):
            variants = grouped[word]
            length = len(word)

            variants_text = self._variants_count_text(len(variants))

            parent = QTreeWidgetItem([word, str(length), variants_text, "?", "🗑"])
            parent.setData(0, Qt.ItemDataRole.UserRole, None)
            parent.setData(3, Qt.ItemDataRole.UserRole, word)
            parent.setData(4, Qt.ItemDataRole.UserRole, word)

            parent.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            parent.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
            parent.setTextAlignment(4, Qt.AlignmentFlag.AlignCenter)

            parent.setToolTip(3, "")
            parent.setToolTip(4, "Скрыть слово из подсказок")

            if word_index < 3:
                for column in range(5):
                    parent.setBackground(column, QColor("#fff1b8"))

            self.results_tree.addTopLevelItem(parent)

            variants.sort(
                key=lambda move: (
                    move.placed_cell.row,
                    move.placed_cell.col,
                    move.letter,
                )
            )

            for move in variants:
                move_index = move_index_by_id[id(move)]

                child = QTreeWidgetItem(
                    [
                        "",
                        "",
                        self._move_variant_text(move),
                        "",
                        "",
                    ]
                )

                child.setData(0, Qt.ItemDataRole.UserRole, move_index)
                parent.addChild(child)

            parent.setExpanded(True)

        for column in range(5):
            self.results_tree.resizeColumnToContents(column)

    def _move_variant_text(self, move: SuggestedMove) -> str:
        row = move.placed_cell.row + 1
        col = move.placed_cell.col + 1
        return f"«{move.letter}» в ({row}, {col})"

    def _variants_count_text(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return f"{count} вариант"

        if 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
            return f"{count} варианта"

        return f"{count} вариантов"

    def _on_result_hovered(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 3:
            self._clear_highlight()
            self.results_tree.setCursor(Qt.CursorShape.PointingHandCursor)
            self._show_definition_popup_for_item(item)
            return

        if column == 4:
            self._clear_highlight()
            self.results_tree.setCursor(Qt.CursorShape.PointingHandCursor)
            self.definition_popup.hide_popup()
            return

        self.results_tree.setCursor(Qt.CursorShape.ArrowCursor)
        self.definition_popup.hide_popup()
        self._show_move_from_item(item)

    def _hide_hint_word_from_item(self, item: QTreeWidgetItem) -> None:
        # Если кликнули по дочернему варианту в колонке мусорки,
        # поднимаемся к родительскому слову.
        parent = item.parent()

        if parent is not None:
            item = parent

        word = normalize_word(item.text(0))

        if not word:
            return

        self.hidden_hint_words.add(word)

        self.current_moves = [
            move
            for move in self.current_moves
            if normalize_word(move.word) != word
        ]

        self._clear_highlight()
        self._refresh_results_table()

        self.status_label.setText(
            f"Слово «{word}» скрыто из подсказок для текущей игры."
        )

    def _on_result_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 3:
            self._ensure_definition_for_item(item)
            return

        if column == 4:
            self._hide_hint_word_from_item(item)
            return

        self._use_move_from_item(item)

    def _show_move_from_item(self, item: QTreeWidgetItem) -> None:
        index = item.data(0, Qt.ItemDataRole.UserRole)

        if index is None:
            self._clear_highlight()
            return

        move = self.current_moves[index]

        if self.preview_base_grid is None:
            self.preview_base_grid = self.board_widget.grid_values()

        self.board_widget.show_move(move, self.preview_base_grid)

    def _use_move_from_item(self, item: QTreeWidgetItem) -> None:
        index = item.data(0, Qt.ItemDataRole.UserRole)

        # Клик по слову ничего не делает.
        # Кликать нужно по конкретному варианту.
        if index is None:
            return

        move = self.current_moves[index]
        self._apply_used_move(move)

    def _apply_used_move(self, move: SuggestedMove) -> None:
        word = normalize_word(move.word)

        if self.preview_base_grid is not None:
            self.board_widget.restore_grid(self.preview_base_grid)
            self.preview_base_grid = None
        else:
            self.board_widget.clear_highlight()

        placed_cell = self.board_widget.cells[move.placed_cell.row][move.placed_cell.col]
        placed_cell.set_value_silent(move.letter)
        placed_cell.set_normal_style()
        placed_cell.setToolTip("")

        if word:
            self.used_words[word] = UsedWordEntry(
                word=word,
                row=move.placed_cell.row,
                col=move.placed_cell.col,
                letter=move.letter,
            )
            self._refresh_used_words_list()

        self.status_label.setText(
            f"Слово «{move.word}» добавлено. Пересчитываю подсказки..."
        )

        self.current_moves = []
        self.results_tree.clear()

        self._start_search()

    def _remove_used_word_by_text(self, clicked_word: str) -> None:
        word = normalize_word(clicked_word)

        if not word:
            return

        entry = self.used_words.pop(word, None)

        if entry is None:
            return

        if entry.row is not None and entry.col is not None:
            cell = self.board_widget.cells[entry.row][entry.col]

            if entry.letter is None or cell.value() == entry.letter:
                cell.set_value_silent("")
                cell.set_normal_style()
                cell.setToolTip("")

        self.preview_base_grid = None
        self.board_widget.clear_highlight()

        self._refresh_used_words_list()

        self.status_label.setText(
            f"Слово «{word}» удалено из использованных."
        )

        self.current_moves = []
        self.results_tree.clear()

    def _refresh_used_words_list(self) -> None:
        words = sorted(self.used_words.keys())
        self.used_words_cloud.set_words(words)
        self.used_words_cloud.adjustSize()