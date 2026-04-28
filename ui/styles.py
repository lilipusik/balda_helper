APP_STYLE = """
QMainWindow {
    background: #f7efe5;
}

QFrame#panel {
    background: #fffaf3;
    border: 1px solid #eadfce;
    border-radius: 24px;
}

QFrame#innerPanel {
    background: transparent;
    border: none;
}

QFrame#boardHolder {
    background: #f3e8dc;
    border: 1px solid #e4d2c0;
    border-radius: 22px;
}

QLabel#title {
    font-size: 34px;
    font-weight: 800;
    color: #4a3f35;
}

QLabel#subtitle {
    font-size: 15px;
    color: #7a6a5d;
}

QLabel#sectionTitle {
    font-size: 22px;
    font-weight: 700;
    color: #4a3f35;
}

QLabel#smallLabel {
    color: #7a6a5d;
    font-size: 12px;
    font-weight: 600;
}

QLabel#status {
    color: #7a6a5d;
    font-size: 14px;
}

QComboBox,
QSpinBox {
    background: #fffaf0;
    border: 2px solid #eadfce;
    border-radius: 10px;
    padding: 6px 10px;
    color: #4a3f35;
    min-height: 28px;
}

QComboBox:focus,
QSpinBox:focus {
    border: 2px solid #d8a7b1;
}

QCheckBox {
    color: #4a3f35;
    font-size: 14px;
    font-weight: 600;
    padding-top: 18px;
}

QPushButton {
    background: #efe1d1;
    border: none;
    border-radius: 14px;
    color: #4a3f35;
    font-weight: 700;
    padding: 11px 16px;
}

QPushButton:hover {
    background: #e5d1bf;
}

QPushButton:pressed {
    background: #d9c0ab;
}

QPushButton#primaryButton {
    background: #d8a7b1;
    color: white;
}

QPushButton#primaryButton:hover {
    background: #c98f9d;
}

QPushButton#primaryButton:disabled {
    background: #dec7cc;
    color: #fff7f8;
}

QTreeWidget {
    background: #fffaf0;
    border: 2px solid #eadfce;
    border-radius: 18px;
    padding: 8px;
    color: #4a3f35;
    font-size: 17px;
    font-weight: 700;
}

QTreeWidget::item {
    padding: 7px;
    border-radius: 10px;
}

QTreeWidget::item:hover {
    background: #f4dfd7;
}

QTreeWidget::item:selected {
    background: #d8f3dc;
    color: #2d4a36;
}

QHeaderView::section {
    background: #f3e8dc;
    color: #7a6a5d;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
    font-weight: 800;
}

QScrollArea {
    background: #fffaf0;
    border: 2px solid #eadfce;
    border-radius: 18px;
}

QScrollArea > QWidget > QWidget {
    background: #fffaf0;
}
"""