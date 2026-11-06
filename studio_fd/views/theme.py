"""Identidade visual: tokens de cor, paleta Qt e folha de estilo única.

As cores ficam em constantes para que widgets pintados à mão (avatar, menu,
tabelas) usem exatamente os mesmos valores da folha de estilo.
"""

from PySide6.QtGui import QColor, QPalette

from studio_fd.utils.paths import resource_root

# Superfícies: do mais escuro (menu) ao mais claro (campos e hover).
SIDEBAR = "#09090B"
BG = "#0E0E10"
SURFACE = "#141417"
RAISED = "#1A1A1E"
HOVER = "#202025"
BORDER = "#232328"
BORDER_STRONG = "#303036"

# Texto em três níveis de ênfase.
TEXT = "#F2F0EB"
TEXT_2 = "#A3A19B"
TEXT_3 = "#6C6B67"

# Dourado é destaque, nunca fundo de área grande.
GOLD = "#C9A96B"
GOLD_HOVER = "#D8BB82"
GOLD_PRESSED = "#B39459"
GOLD_INK = "#16130D"
GOLD_TINT = "#1F1B14"
GOLD_LINE = "#3B3324"

SUCCESS = "#8DBF9B"
SUCCESS_TINT = "#16231B"
SUCCESS_LINE = "#23392A"
DANGER = "#E39385"
DANGER_TINT = "#2A1815"
DANGER_LINE = "#4A2A24"


def apply_palette(app) -> None:
    """Garante fundos escuros em áreas que a folha de estilo não alcança."""
    palette = QPalette()
    for role, color in {
        QPalette.ColorRole.Window: BG, QPalette.ColorRole.Base: RAISED,
        QPalette.ColorRole.AlternateBase: SURFACE, QPalette.ColorRole.Button: RAISED,
        QPalette.ColorRole.Text: TEXT, QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.ButtonText: TEXT, QPalette.ColorRole.PlaceholderText: TEXT_3,
        QPalette.ColorRole.Highlight: GOLD_LINE, QPalette.ColorRole.HighlightedText: TEXT,
        QPalette.ColorRole.ToolTipBase: RAISED, QPalette.ColorRole.ToolTipText: TEXT,
    }.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)


STYLESHEET = """
* { font-family: 'Segoe UI'; }
QWidget { color: @TEXT@; font-size: 13px; background: transparent; }
QMainWindow, QDialog, QMessageBox { background: @BG@; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QStackedWidget { background: @BG@; }
QToolTip { background: @RAISED@; color: @TEXT@; border: 1px solid @BORDER_STRONG@; padding: 6px 8px; border-radius: 6px; }

/* Menu lateral */
QWidget#sidebar { background: @SIDEBAR@; border-right: 1px solid @BORDER@; }
QScrollArea#sidebarScroll { background: @SIDEBAR@; }
QLabel#brandMonogram { background: @GOLD_TINT@; border: 1px solid @GOLD_LINE@; border-radius: 10px;
    color: @GOLD@; font-family: Georgia; font-size: 17px; }
QLabel#brandName { font-size: 14px; font-weight: 600; letter-spacing: 0.2px; }
QLabel#brandTagline { color: @TEXT_3@; font-size: 11px; letter-spacing: 1.6px; }
QLabel#navSection { color: @TEXT_3@; font-size: 10px; font-weight: 600; letter-spacing: 1.4px; padding-left: 12px; }
QFrame#sidebarFooter { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 10px; }

/* Tipografia */
QLabel#eyebrow { color: @GOLD@; font-size: 11px; font-weight: 600; letter-spacing: 1.6px; }
QLabel#title { font-size: 26px; font-weight: 600; letter-spacing: -0.3px; }
QLabel#dialogTitle { font-size: 20px; font-weight: 600; letter-spacing: -0.2px; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#strong { font-weight: 600; }
QLabel#muted { color: @TEXT_2@; }
QLabel#caption { color: @TEXT_3@; font-size: 12px; }
QLabel#fieldLabel { color: @TEXT_3@; font-size: 11px; font-weight: 600; letter-spacing: 0.8px; }
QLabel#fieldValue { font-size: 13px; }
QLabel#metricLabel { color: @TEXT_2@; font-size: 12px; }
QLabel#metricValue, QLabel#metricAccent { font-size: 28px; font-weight: 600; letter-spacing: -0.4px; }
QLabel#statValue { font-size: 17px; font-weight: 600; }
QLabel#formError { color: @DANGER@; }

/* Etiquetas de status */
QLabel#pill { border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 600; }
QLabel#pill[tone="success"] { background: #16231B; color: @SUCCESS@; border: 1px solid #23392A; }
QLabel#pill[tone="muted"] { background: @RAISED@; color: @TEXT_3@; border: 1px solid @BORDER@; }
QLabel#pill[tone="gold"] { background: @GOLD_TINT@; color: @GOLD@; border: 1px solid @GOLD_LINE@; }
QLabel#pill[tone="danger"] { background: @DANGER_TINT@; color: @DANGER@; border: 1px solid @DANGER_LINE@; }

/* Superfícies */
QFrame#panel, QFrame#metricCard { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 14px; }
QFrame#metricCard:hover { border-color: #2E2B26; }
QFrame#heroPanel { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #17150F, stop:0.55 @SURFACE@, stop:1 @SURFACE@);
    border: 1px solid @GOLD_LINE@; border-radius: 16px; }
QFrame#softPanel { background: @SURFACE@; border: 1px dashed @BORDER_STRONG@; border-radius: 12px; }
QFrame#planCard { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 12px; }
QFrame#planCard:hover { border-color: @GOLD_LINE@; background: #16161A; }
QFrame#newCard { background: transparent; border: 1px dashed @BORDER_STRONG@; border-radius: 12px; }
QFrame#newCard:hover { border-color: @GOLD@; }
QFrame#divider { background: @BORDER@; max-height: 1px; min-height: 1px; border: none; }
QFrame#dialogFooter { background: @SIDEBAR@; border-top: 1px solid @BORDER@; }
QFrame#recipient { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 12px; }

/* Botões */
QPushButton { background: @RAISED@; border: 1px solid @BORDER_STRONG@; border-radius: 8px;
    padding: 8px 14px; font-weight: 600; color: @TEXT@; }
QPushButton:hover { background: @HOVER@; border-color: #3E3E45; }
QPushButton:pressed { background: @SURFACE@; }
QPushButton:focus { border-color: @GOLD@; }
QPushButton:disabled { color: @TEXT_3@; border-color: @BORDER@; background: @SURFACE@; }
QPushButton#primaryButton { background: @GOLD@; border-color: @GOLD@; color: @GOLD_INK@; }
QPushButton#primaryButton:hover { background: @GOLD_HOVER@; border-color: @GOLD_HOVER@; }
QPushButton#primaryButton:pressed { background: @GOLD_PRESSED@; }
QPushButton#primaryButton:focus { border-color: @TEXT@; }
QPushButton#ghostButton { background: transparent; border-color: transparent; color: @TEXT_2@; }
QPushButton#ghostButton:hover { background: @RAISED@; color: @TEXT@; }
QPushButton#letterButton { background: transparent; border: none; border-radius: 6px; padding: 5px 0;
    min-width: 22px; color: @TEXT_2@; font-weight: 600; font-size: 12px; }
QPushButton#letterButton[empty="true"] { color: #45443F; }
QPushButton#letterButton:hover { background: @RAISED@; color: @TEXT@; }
QPushButton#letterButton:checked { background: @GOLD_TINT@; color: @GOLD@; }
QPushButton#letterButton[wide="true"] { padding: 5px 10px; }
QPushButton#iconButton { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 10px; padding: 0; }
QPushButton#iconButton:hover { background: @RAISED@; border-color: @GOLD_LINE@; }
QPushButton#dateLabel { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 10px; padding: 7px 16px;
    font-size: 13px; font-weight: 600; text-align: center; }
QPushButton#dateLabel:hover { border-color: @GOLD_LINE@; background: @RAISED@; }
QPushButton#dangerButton { background: @DANGER_TINT@; border-color: @DANGER_LINE@; color: @DANGER@; }
QPushButton#dangerButton:hover { background: #351E1A; border-color: @DANGER@; }
QPushButton#sidebarToggle { background: transparent; border: none; border-radius: 8px; padding: 0; }
QPushButton#sidebarToggle:hover { background: @RAISED@; }
QPushButton#paletteHint { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 9px; padding: 7px 12px;
    color: @TEXT_3@; font-weight: 400; text-align: left; }
QPushButton#paletteHint:hover { border-color: @GOLD_LINE@; color: @TEXT_2@; }

/* Campos */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {
    background: @RAISED@; color: @TEXT@; border: 1px solid @BORDER_STRONG@; border-radius: 8px;
    padding: 7px 10px; selection-background-color: @GOLD_LINE@; min-height: 20px;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QTextEdit:hover { border-color: #3E3E45; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus { border-color: @GOLD@; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled { color: @TEXT_3@; background: @SURFACE@; border-color: @BORDER@; }
QLineEdit#searchField { padding-left: 6px; }
QComboBox QAbstractItemView { background: @RAISED@; border: 1px solid @BORDER_STRONG@; border-radius: 8px;
    selection-background-color: @GOLD_TINT@; selection-color: @GOLD@; padding: 4px; outline: none; }
QComboBox, QDateEdit { padding-right: 30px; }
QComboBox::drop-down, QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 28px; border: none; }
QComboBox::down-arrow, QDateEdit::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 11px; height: 11px; }
QSpinBox, QDoubleSpinBox { padding-right: 28px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 24px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; border: none; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("@ASSETS@/chevron-up.svg"); width: 10px; height: 10px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 10px; height: 10px; }
QCheckBox { spacing: 8px; color: @TEXT_2@; }
QCheckBox:hover { color: @TEXT@; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #4A4A51; border-radius: 4px; background: @RAISED@; }
QCheckBox::indicator:hover { border-color: @GOLD@; }
QCheckBox::indicator:checked { background: @GOLD@; border-color: @GOLD@; image: url("@ASSETS@/check.svg"); }
QCalendarWidget QWidget { background: @RAISED@; color: @TEXT@; alternate-background-color: @RAISED@; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: @RAISED@; border-bottom: 1px solid @BORDER@; }
QCalendarWidget QToolButton { background: transparent; color: @TEXT@; border: none; padding: 6px 10px; font-weight: 600; border-radius: 6px; }
QCalendarWidget QToolButton:hover { background: @HOVER@; }
QCalendarWidget QToolButton::menu-indicator { image: none; }
QCalendarWidget QAbstractItemView { selection-background-color: @GOLD@; selection-color: @GOLD_INK@; outline: none; }
QCalendarWidget QAbstractItemView:disabled { color: @TEXT_3@; }

/* Menus de ação e listas suspensas */
QMenu { background: @RAISED@; border: 1px solid @BORDER_STRONG@; border-radius: 12px; padding: 6px; }
QMenu::item { padding: 8px 18px 8px 12px; border-radius: 7px; color: @TEXT@; background: transparent; }
QMenu::item:selected { background: @HOVER@; color: @GOLD_HOVER@; }
QMenu::item:disabled { color: @TEXT_3@; }
QMenu::icon { padding-left: 8px; }
QMenu::separator { height: 1px; background: @BORDER@; margin: 5px 8px; }
QListView#completerPopup, QListWidget#paletteList { background: @RAISED@; border: 1px solid @BORDER_STRONG@; border-radius: 10px;
    padding: 4px; outline: none; }
QListView#completerPopup::item { padding: 7px 10px; border-radius: 6px; }
QListView#completerPopup::item:selected { background: @GOLD_TINT@; color: @GOLD@; }

/* Seções dos formulários: título discreto acima de um cartão */
QGroupBox { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 12px;
    margin-top: 26px; padding: 18px 16px 14px 16px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 2px; top: 0px;
    color: @TEXT_3@; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
QFormLayout QLabel, QGroupBox QLabel { color: @TEXT_2@; }

/* Tabelas */
QTableView { background: transparent; border: none; gridline-color: transparent; outline: none;
    selection-background-color: transparent; }
QHeaderView { background: transparent; border: none; }
QHeaderView::section { background: transparent; color: @TEXT_3@; border: none; border-bottom: 1px solid @BORDER@;
    padding: 0 16px; height: 38px; font-size: 11px; font-weight: 600; letter-spacing: 0.8px; }

/* Rolagem */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2C2C32; border-radius: 3px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3A3A41; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2C2C32; border-radius: 3px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QStatusBar { background: @SIDEBAR@; color: @TEXT_3@; border-top: 1px solid @BORDER@; font-size: 11px; }
QStatusBar::item { border: none; }
QMessageBox QLabel { color: @TEXT@; }
"""

for _name, _value in sorted(dict(globals()).items(), key=lambda item: -len(item[0])):
    if _name.isupper() and isinstance(_value, str) and _value.startswith("#"):
        STYLESHEET = STYLESHEET.replace(f"@{_name}@", _value)
STYLESHEET = STYLESHEET.replace("@ASSETS@", (resource_root() / "assets").as_posix())
