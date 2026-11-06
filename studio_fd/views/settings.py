"""Configurações: personais (colunas da agenda) e horário de funcionamento."""

from PySide6.QtCore import QTime, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QTimeEdit, QWidget

from studio_fd import __version__
from studio_fd.services.settings_service import SettingsService
from studio_fd.utils.paths import AppPaths
from studio_fd.views.dashboard import clear
from studio_fd.widgets.motion import toast
from studio_fd.views import theme
from studio_fd.widgets.visuals import Avatar, icon_button, icon_label, label, page_header, page_layout, panel


class TrainerRow(QWidget):
    def __init__(self, view: "SettingsView", trainer=None):
        super().__init__()
        self.view, self.trainer = view, trainer
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(12)
        if trainer:
            row.addWidget(Avatar(trainer.name, 36))
        else:
            badge = icon_label("plus", theme.GOLD, 18)
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(badge)
        self.name = QLineEdit(trainer.name if trainer else "")
        self.name.setPlaceholderText("Nome do novo personal")
        self.name.setMaxLength(80)
        self.active = QCheckBox("Ativo na agenda")
        self.active.setChecked(trainer.active if trainer else True)
        save = QPushButton("Salvar" if trainer else "Adicionar")
        save.setObjectName("" if trainer else "primaryButton")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.save)
        self.name.returnPressed.connect(self.save)
        row.addWidget(self.name, 1)
        row.addWidget(self.active)
        row.addWidget(save)

    def save(self) -> None:
        try:
            self.view.service.save_trainer(self.name.text(), self.active.isChecked(), self.trainer.id if self.trainer else None)
        except ValueError as error:
            toast(self, str(error), "error")
            return
        toast(self, "Personal salvo")
        self.view.refresh()
        self.view.changed.emit()


class SettingsView(QWidget):
    changed = Signal()

    def __init__(self, service: SettingsService, paths: AppPaths):
        super().__init__()
        self.service = service
        layout = page_layout(self)
        layout.addLayout(page_header("SISTEMA", "Configurações", label("Personais e horário de funcionamento definem as vagas da agenda.")))

        trainers, trainers_layout = panel(margins=(22, 18, 22, 18), spacing=6)
        trainers_layout.addWidget(label("Personais", "sectionTitle"))
        trainers_layout.addWidget(label("Cada personal ativo é uma coluna da agenda: com 2 ativos, cada horário aceita até 2 alunos.", "caption"))
        self.trainer_list = QGridLayout()
        self.trainer_list.setVerticalSpacing(4)
        trainers_layout.addLayout(self.trainer_list)
        layout.addWidget(trainers)

        hours, hours_layout = panel(margins=(22, 18, 22, 20), spacing=12)
        hours_layout.addWidget(label("Horário de funcionamento", "sectionTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        self.open_time = QTimeEdit()
        self.close_time = QTimeEdit()
        for editor in (self.open_time, self.close_time):
            editor.setDisplayFormat("HH:mm")
        self.slot = QComboBox()
        for minutes in (30, 45, 60, 90):
            self.slot.addItem(f"{minutes} minutos", minutes)
        for column, (text, widget) in enumerate((("ABERTURA", self.open_time), ("FECHAMENTO", self.close_time), ("CADA ATENDIMENTO", self.slot))):
            grid.addWidget(label(text, "fieldLabel", wrap=False), 0, column)
            grid.addWidget(widget, 1, column)
            grid.setColumnStretch(column, 1)
        save = icon_button("Salvar horário", "check", "primaryButton")
        save.clicked.connect(self.save_hours)
        grid.addWidget(save, 1, 3)
        hours_layout.addLayout(grid)
        self.preview = label("", "caption")
        hours_layout.addWidget(self.preview)
        layout.addWidget(hours)

        data, data_layout = panel(margins=(22, 18, 22, 18), spacing=8)
        data_layout.addWidget(label("Dados do aplicativo", "sectionTitle"))
        path = label(str(paths.root), "muted")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        data_layout.addWidget(path)
        data_layout.addWidget(label(f"Versão {__version__}  ·  banco, contratos e backups ficam separados do programa e "
                                    "são preservados nas atualizações.", "caption"))
        open_folder = icon_button("Abrir pasta de dados", "folder", "ghostButton")
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.root))))
        data_layout.addWidget(open_folder, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(data)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        clear(self.trainer_list)
        trainers = self.service.trainers()
        for index, trainer in enumerate(trainers):
            self.trainer_list.addWidget(TrainerRow(self, trainer), index, 0)
        self.trainer_list.addWidget(TrainerRow(self), len(trainers), 0)
        hours = self.service.hours()
        self.open_time.setTime(QTime.fromString(hours.open_time, "HH:mm"))
        self.close_time.setTime(QTime.fromString(hours.close_time, "HH:mm"))
        self.slot.setCurrentIndex(max(0, self.slot.findData(hours.slot_minutes)))
        slots = hours.slots()
        self.preview.setText(f"{len(slots)} horários por dia: {slots[0]} até {slots[-1]}" if slots else "")

    def save_hours(self) -> None:
        try:
            self.service.save_hours(self.open_time.time().toString("HH:mm"), self.close_time.time().toString("HH:mm"), self.slot.currentData())
        except ValueError as error:
            toast(self, str(error), "error")
            return
        toast(self, "Horário salvo")
        self.refresh()
        self.changed.emit()
