"""Uma única folha de estilo mantém a identidade visual consistente."""

from studio_fd.utils.paths import resource_root

STYLESHEET = """
QWidget { background: #111214; color: #ededee; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QScrollArea, QStackedWidget { background: #111214; }
QScrollArea { border: none; }
QLabel { background: transparent; }
QFrame#sidebar { background: #0c0d0f; border-right: 1px solid #28292c; }
QLabel#brandMonogram { color: #d6b776; font-family: Georgia; font-size: 52px; }
QLabel#brandTitle { font-size: 15px; font-weight: 600; letter-spacing: 3px; }
QLabel#brandSubtitle { color: #a68d5d; font-size: 10px; letter-spacing: 3px; }
QLabel#eyebrow { color: #bba16d; font-size: 11px; font-weight: 600; letter-spacing: 2px; }
QLabel#title { font-size: 28px; font-weight: 600; }
QLabel#sectionTitle { font-size: 16px; font-weight: 600; }
QLabel#muted { color: #a7a8ad; }
QLabel#caption { color: #8b8d95; font-size: 11px; }
QLabel#metricValue { font-size: 30px; font-weight: 600; }
QLabel#metricAccent { color: #d6b776; font-size: 30px; font-weight: 600; }
QFrame#metricCard, QFrame#panel { background: #1a1b1f; border: 1px solid #2b2c31; border-radius: 10px; }
QFrame#welcomePanel { background: #201e19; border: 1px solid #3d3526; border-radius: 10px; }
QPushButton { background: #24252a; border: 1px solid #3b3c42; border-radius: 6px; padding: 9px 15px; }
QPushButton:hover { background: #303137; border-color: #9b8354; }
QPushButton:pressed { background: #3b3528; }
QPushButton:focus { border-color: #d6b776; }
QPushButton#navButton { text-align: left; background: transparent; border: 1px solid transparent; padding: 11px 16px; color: #a7a8ad; }
QPushButton#navButton:hover { background: #1b1c20; color: #ededee; }
QPushButton#navButton:checked { background: #29251d; color: #e1c486; border: 1px solid #453a26; }
QPushButton#navButton:focus { border-color: #d6b776; }
QLabel#badge { background: #26271f; color: #c4cba8; border: 1px solid #3b3f2f; border-radius: 5px; padding: 5px 9px; font-size: 11px; }
QHeaderView::section { background: #202126; color: #a7a8ad; border: none; padding: 13px; font-size: 11px; }
QTableWidget { background: #1a1b1f; border: none; gridline-color: #303137; selection-background-color: #363021; }
QTableWidget::item { padding: 10px; }
QStatusBar { background: #0c0d0f; color: #8b8d95; border-top: 1px solid #28292c; font-size: 11px; }
QStatusBar::item { border: none; }
QScrollBar:vertical { background: #111214; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #3b3c42; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #28292d; color: #ededee; border: 1px solid #645336; padding: 6px; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
    background: #202126; color: #ededee; border: 1px solid #44454c; border-radius: 5px;
    padding: 8px; selection-background-color: #645336;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus { border-color: #d6b776; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled { color: #777980; background: #191a1e; }
QComboBox QAbstractItemView { background: #202126; selection-background-color: #453a26; padding: 4px; }
QGroupBox { border: 1px solid #34353b; border-radius: 7px; margin-top: 12px; padding: 14px 8px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #d6b776; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #85868d; border-radius: 3px; background: #202126; }
QCheckBox::indicator:checked { background: #d6b776; border-color: #d6b776; image: url("@ASSETS@/check.svg"); }
QCheckBox::indicator:hover { border-color: #d6b776; }
QComboBox, QDateEdit { padding-right: 28px; }
QComboBox::drop-down, QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border: none; }
QComboBox::down-arrow, QDateEdit::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 12px; height: 12px; }
QSpinBox, QDoubleSpinBox { padding-right: 26px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; border: none; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("@ASSETS@/chevron-up.svg"); width: 12px; height: 12px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 12px; height: 12px; }
QPushButton#primaryButton { background: #d6b776; border-color: #d6b776; color: #171511; font-weight: 600; }
QPushButton#primaryButton:hover { background: #e5ca95; }
QPushButton#primaryButton:pressed { background: #baa068; }
QPushButton#letterButton { padding: 7px 3px; min-width: 26px; }
QPushButton#letterButton:checked { background: #453a26; border-color: #bba16d; color: #e5ca95; }
QPushButton:disabled { color: #73757c; border-color: #34353b; }
QLabel#formError { color: #f0a49c; }
""".replace("@ASSETS@", (resource_root() / "assets").as_posix())
