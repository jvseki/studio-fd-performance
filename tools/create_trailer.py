"""Grava a interface real com dados fictícios e monta um trailer em MP4.

A interface é operada por um roteiro: pesquisa, ficha, WhatsApp, cadastro e
planos acontecem de verdade num banco temporário. Nada é enviado; nenhum dado
do Studio é lido. Requer imageio-ffmpeg em build/video-tools.

    .venv\\Scripts\\python.exe tools\\create_trailer.py            # vídeo completo
    .venv\\Scripts\\python.exe tools\\create_trailer.py --preview  # um quadro por cena
"""

import argparse
from array import array
from datetime import date, timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "build/video-tools"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QLocale, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen, QPolygonF,
)
from PySide6.QtWidgets import QApplication, QPushButton

from studio_fd.database.migrations import migrate_database
from studio_fd.database.session import create_database_engine, create_session_factory
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.services.plan_service import PlanService
from studio_fd.services.records import PlanInput, StudentInput
from studio_fd.services.student_service import StudentService
from studio_fd.utils.paths import AppPaths
from studio_fd.views import theme
from studio_fd.views.main_window import MainWindow
from studio_fd.views.student_form import StudentDialog
from studio_fd.views.student_profile import StudentProfile
from studio_fd.views.theme import STYLESHEET, apply_palette
from studio_fd.views.whatsapp import WhatsAppDialog
from studio_fd.widgets.icons import pixmap

W, H, FPS = 1920, 1080, 30
APP_W, APP_H = 1366, 820
BG = QColor("#08080A")

# (segundos, numeração, título, texto, aproximação da câmera)
SCENES = [
    (4.5, "", "", "", 1.0),
    (7, "VISÃO GERAL", "O dia do Studio\nem uma tela.", "Receita prevista, vencimentos\ne alunos por plano, a partir\ndos cadastros.", 1.035),
    (8, "ALUNOS", "Encontre qualquer\naluno em segundos.", "Pesquise pelo nome ou pela\ninicial e abra a ficha\ncom um clique.", 1.035),
    (7, "FICHA DO ALUNO", "Tudo o que importa\nno atendimento.", "Plano, mensalidade, vencimento\ne observações de cada aluno.", 1.035),
    (7, "WHATSAPP", "Contato pessoal,\nsem copiar e colar.", "A mensagem sai pronta.\nVocê revisa e envia\npelo seu WhatsApp.", 1.035),
    (8, "CADASTRO", "Novo aluno em\nmenos de um minuto.", "Nome, telefone e plano.\nO valor vem do plano e\npode ser ajustado.", 1.035),
    (6.5, "PLANOS", "Os seus planos,\ndo seu jeito.", "Frequência, valor e duração\ndefinidos pelo Studio.", 1.035),
    (6.5, "", "", "", 1.0),
    (6, "", "", "", 1.0),
]
DURATION = sum(scene[0] for scene in SCENES)
FRAME = QRectF(600, 150, 1250, 36 + APP_H * 1250 / APP_W)
TITLEBAR = 36


def ease(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def ease_out(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return 1 - (1 - value) ** 3


def font(size: int, weight=QFont.Weight.Normal, family: str = "Segoe UI", spacing: float = 0) -> QFont:
    result = QFont(family)
    result.setPixelSize(size)
    result.setWeight(weight)
    if spacing:
        result.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return result


def text(p: QPainter, rect, content: str, size: int, color: str = theme.TEXT, weight=QFont.Weight.Normal,
         align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, spacing: float = 0, family: str = "Segoe UI") -> None:
    p.setFont(font(size, weight, family, spacing))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), align | Qt.TextFlag.TextWordWrap, content)


def rounded(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def shadow(p: QPainter, rect: QRectF, radius: float, spread: int = 34, strength: int = 7) -> None:
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    for step in range(spread, 0, -3):
        p.setBrush(QColor(0, 0, 0, strength))
        p.drawPath(rounded(rect.adjusted(-step, -step + 14, step, step + 14), radius + step))
    p.restore()


def soundtrack(path: Path) -> None:
    """Trilha instrumental sintetizada para o vídeo, sem gravações de terceiros."""
    rate = 22050
    chords = [(146.832, 174.614, 220.0, 261.626), (130.813, 164.814, 195.998, 246.942),
              (110.0, 130.813, 164.814, 195.998), (116.541, 146.832, 174.614, 220.0)]
    total = math.ceil(DURATION)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        for second in range(total):
            samples = array("h")
            for i in range(rate):
                t = second + i / rate
                chord = chords[int(t / 4) % 4]
                local = t % 4
                envelope = min(1, local / .4) * min(1, (4 - local) / .6)
                pad = sum(math.sin(2 * math.pi * f * t) + .3 * math.sin(4 * math.pi * f * t) for f in chord) * .018 * envelope
                delta = t % .5
                note = chord[int(t / .5) % 4] * 2
                pluck = math.sin(2 * math.pi * note * delta) * math.exp(-delta * 8) * .06
                pulse_time = t % 1
                pulse = math.sin(2 * math.pi * 55 * pulse_time) * math.exp(-pulse_time * 18) * .05
                fade = min(1, t / 2.5) * min(1, max(0, DURATION - t) / 3.5)
                left = (pad + pluck + pulse) * fade
                right = (pad + pluck * .85 + pulse) * fade
                samples.extend((int(32767 * left), int(32767 * right)))
            output.writeframes(samples.tobytes())


class Trailer:
    def __init__(self, app: QApplication, paths: AppPaths):
        self.app = app
        self.engine = create_database_engine(paths.database)
        migrate_database(self.engine)
        sessions = create_session_factory(self.engine)
        self.plans = PlanService(sessions)
        self.students = StudentService(sessions)
        self.seed()
        self.window = MainWindow(DashboardService(sessions), paths, self.students, self.plans)
        self.window.resize(APP_W, APP_H)
        self.window.show()
        self.app.processEvents()
        self.dialog = None
        self.scene = -1
        self.saved = None
        self.previous: QImage | None = None
        self.last: QImage | None = None
        self.cursor = QPointF(APP_W * .62, APP_H * .62)

    def seed(self) -> None:
        essential = self.plans.save(PlanInput("Essencial 2x", 2, 32000, 1, "Duas sessões semanais com acompanhamento individual."))
        self.performance = self.plans.save(PlanInput("Performance 3x", 3, 45000, 1, "O plano mais escolhido: três sessões por semana."))
        elite = self.plans.save(PlanInput("Elite 5x", 5, 68000, 1, "Treino diário com o personal."))
        self.plans.save(PlanInput("Trimestral 3x", 3, 123000, 3, "Três meses com valor fechado."))
        today = date.today()
        soon = lambda days: (today + timedelta(days=days)).day
        people = [
            ("Ana Beatriz Souza", self.performance, soon(0)), ("Bruno Carvalho", essential, soon(2)),
            ("Carla Mendes", elite, soon(9)), ("Diego Martins", self.performance, soon(4)),
            ("Fernanda Lima", essential, soon(12)), ("João Pedro Alves", self.performance, soon(15)),
            ("Juliana Rocha", elite, soon(1)), ("Lucas Ferreira", self.performance, soon(20)),
            ("Patrícia Gomes", self.performance, soon(6)), ("Rafael Nogueira", essential, soon(18)),
            ("Thiago Barros", elite, soon(25)), ("Vanessa Prado", self.performance, soon(11)),
        ]
        for index, (name, plan, due) in enumerate(people):
            record = self.students.save(StudentInput(
                name, f"(18) 99{index:02d}1-{4000 + index * 37}", plan_id=plan.id, monthly_fee_cents=plan.price_cents,
                due_day=due, starts_on=date(2026, 2, 2 + index),
                notes="Lesão antiga no joelho direito. Priorizar exercícios sem impacto." if name == "Juliana Rocha" else None))
            if name == "Juliana Rocha":
                self.juliana = record
        self.students.save(StudentInput("Marcos Ribeiro", "(18) 99812-3344", active=False))

    # ---------- posições de elementos da interface ----------
    def center_of(self, widget, root) -> QPointF:
        point = widget.mapTo(root, widget.rect().center())
        return QPointF(point.x(), point.y())

    def button(self, root, label: str) -> QPushButton:
        for button in root.findChildren(QPushButton):
            if button.text() == label and button.isVisible():
                return button
        raise LookupError(label)

    def dialog_offset(self) -> QPointF:
        return QPointF((APP_W - self.dialog.width()) / 2, (APP_H - self.dialog.height()) / 2)

    def in_dialog(self, widget) -> QPointF:
        return self.center_of(widget, self.dialog) + self.dialog_offset()

    # ---------- cenas ----------
    def close_dialog(self) -> None:
        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    def enter(self, scene: int) -> None:
        self.close_dialog()
        self.scene = scene
        nav = self.window.navigation
        if scene == 1:
            nav.button(0).click()
        elif scene == 2:
            nav.button(2).click()
            self.window.students.clear_filters()
        elif scene == 3:
            self.dialog = StudentProfile(self.juliana.id, self.students, self.plans)
            self.dialog.resize(760, 700)
            self.dialog.show()
        elif scene == 4:
            self.dialog = WhatsAppDialog(self.students.get(self.juliana.id))
            self.dialog.resize(640, 540)
            self.dialog.show()
            self.dialog.message.clear()
        elif scene == 5:
            self.window.students.clear_filters()
            self.window.students.table.hovered_row = -1
            self.dialog = StudentDialog(self.students, self.plans)
            self.dialog.resize(680, 700)
            self.dialog.show()
        elif scene == 6:
            nav.button(3).click()
        self.app.processEvents()

    def move(self, start: QPointF, end: QPointF, t0: float, t1: float, elapsed: float) -> None:
        if elapsed <= t0:
            self.cursor = QPointF(start)
        else:
            k = ease(min(1, (elapsed - t0) / (t1 - t0)))
            self.cursor = start + (end - start) * k

    def app_shot(self, scene: int, t: float):
        """Retorna (imagem da interface, progresso do clique, aviso, mostrar cursor)."""
        click = None
        toast = None
        if scene == 1:
            self.cursor = QPointF(APP_W * .9, APP_H * .95)
            return self.window.grab().toImage(), None, None, False
        if scene == 2:
            view = self.window.students
            search = self.center_of(view.search, self.window) - QPointF(view.search.width() * .32, 0)
            query = "" if t < 2.6 else "Jul"[:min(3, int((t - 2.6) * 6) + 1)]
            if view.search.text() != query:
                view.search.setText(query)
                view.refresh()
            self.app.processEvents()
            row_rect = view.table.visualRect(view.table.model().index(0, 0))
            row_point = view.table.viewport().mapTo(self.window, row_rect.center())
            row = QPointF(row_point.x() - 30, row_point.y())
            self.move(QPointF(APP_W * .62, APP_H * .7), search, .6, 2.2, t)
            if t > 3.6:
                self.move(search, row, 3.8, 5.4, t)
            view.table.hovered_row = 0 if t > 5.1 else -1
            view.table.viewport().update()
            if 5.9 < t < 6.6:
                click = (t - 5.9) / .7
            if t > 6.2:
                view.table.selectRow(0)
            return self.window.grab().toImage(), click, None, True
        if scene in (3, 4, 5):
            backdrop = self.window.grab().toImage()
            if scene == 3:
                target = self.in_dialog(self.dialog.whatsapp)
                self.move(QPointF(APP_W * .5, APP_H * .8), target, 4.2, 5.6, t)
                if 5.9 < t < 6.6:
                    click = (t - 5.9) / .7
                    self.dialog.whatsapp.setDown(t < 6.2)
            elif scene == 4:
                message = ("Oi, Juliana! Tudo bem?\n\nPassando para lembrar do seu treino de amanhã aqui no "
                           "Studio FD Performance. Qualquer coisa, é só chamar!")
                count = max(0, min(len(message), int((t - .8) * 34)))
                if self.dialog.message.toPlainText() != message[:count]:
                    self.dialog.message.setPlainText(message[:count])
                    cursor = self.dialog.message.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.dialog.message.setTextCursor(cursor)
                target = self.in_dialog(self.dialog.save_button)
                self.move(QPointF(APP_W * .6, APP_H * .5), target, 4.6, 5.8, t)
                self.dialog.save_button.setDown(5.95 < t < 6.25)
                if 5.95 < t < 6.6:
                    click = (t - 5.95) / .65
            elif scene == 5:
                return self.register_shot(backdrop, t)
            self.app.processEvents()
            return self.compose(backdrop, self.dialog.grab().toImage()), click, None, True
        if scene == 6:
            cards = self.window.plans.cards
            target = self.center_of(cards[2], self.window) if len(cards) > 2 else QPointF(APP_W * .7, APP_H * .4)
            self.move(QPointF(APP_W * .85, APP_H * .8), target, .8, 2.6, t)
            return self.window.grab().toImage(), None, None, True
        return None, None, None, False

    def register_shot(self, backdrop: QImage, t: float):
        dialog = self.dialog
        click = None
        if self.saved is not None:
            return self.cache_saved, None, "Aluno cadastrado", True
        name = "Marina Costa"[:max(0, min(12, int((t - .5) * 9)))]
        phone = "(18) 99777-1020"[:max(0, min(15, int((t - 2.2) * 14)))]
        if dialog.name.text() != name:
            dialog.name.setText(name)
        if dialog.phone.text() != phone:
            dialog.phone.setText(phone)
            dialog.phone.setFocus()
        if t >= 3.8 and dialog.plan.currentData() != self.performance.id:
            dialog.plan.setCurrentIndex(dialog.plan.findData(self.performance.id))
            dialog.apply_plan_price()
            dialog.due_day.setValue(10)
        plan_point = self.in_dialog(dialog.plan)
        save_point = self.in_dialog(dialog.save_button)
        self.move(QPointF(APP_W * .5, APP_H * .85), plan_point, 2.6, 3.6, t)
        if t > 3.6:
            self.move(plan_point, save_point, 4.6, 5.8, t)
        if 3.55 < t < 4.1:
            click = (t - 3.55) / .55
        if 6.0 < t < 6.6:
            click = (t - 6.0) / .6
        dialog.save_button.setDown(6.0 < t < 6.3)
        self.app.processEvents()
        frame = self.compose(backdrop, dialog.grab().toImage())
        if t >= 6.35:
            dialog.save_button.setDown(False)
            dialog.save_button.click()
            assert dialog.saved_record is not None, dialog.feedback.text()
            self.saved = dialog.saved_record
            assert self.students.get(self.saved.id).full_name == "Marina Costa"
            self.cache_saved = frame
            return frame, click, "Aluno cadastrado", True
        return frame, click, None, True

    def compose(self, backdrop: QImage, dialog: QImage) -> QImage:
        image = QImage(backdrop)
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(image.rect(), QColor(0, 0, 0, 165))
        offset = self.dialog_offset()
        rect = QRectF(offset.x(), offset.y(), dialog.width(), dialog.height())
        shadow(p, rect, 10, 24, 10)
        p.setClipPath(rounded(rect, 10))
        p.drawImage(rect.topLeft(), dialog)
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(rounded(rect.adjusted(.5, .5, -.5, -.5), 10))
        p.end()
        return image

    # ---------- desenho ----------
    def background(self, p: QPainter, absolute: float) -> None:
        # Fundo liso: gradientes escuros criam faixas visíveis depois da compressão.
        p.fillRect(QRectF(0, 0, W, H), BG)

    def draw_window(self, p: QPainter, shot: QImage, scene: int, t: float, alpha: float) -> None:
        duration, _eyebrow, _title, _body, zoom = SCENES[scene]
        rise = (1 - ease_out(min(1, t / .7))) * 26 if scene == 1 else 0
        outer = FRAME.translated(0, rise)
        # "Câmera" aproximando devagar: a janela inteira cresce em torno do centro.
        z = 1 + (zoom - 1) * ease(t / duration)
        center = outer.center()
        p.save()
        p.translate(center)
        p.scale(z, z)
        p.translate(-center)
        p.setOpacity(alpha)
        shadow(p, outer, 16, 40, 6)
        p.setClipPath(rounded(outer, 14))
        p.fillRect(outer, QColor(theme.SIDEBAR))
        bar = QRectF(outer.left(), outer.top(), outer.width(), TITLEBAR)
        p.fillRect(bar, QColor("#0B0B0D"))
        text(p, (bar.left() + 18, bar.top(), 600, TITLEBAR), "Studio FD Performance", 13, theme.TEXT_3,
             align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        p.setPen(QPen(QColor(theme.TEXT_3), 1.2))
        right = bar.right() - 22
        y = bar.center().y()
        p.drawLine(QPointF(right - 98, y), QPointF(right - 88, y))
        p.drawRect(QRectF(right - 54, y - 5, 10, 10))
        p.drawLine(QPointF(right - 10, y - 5), QPointF(right, y + 5))
        p.drawLine(QPointF(right, y - 5), QPointF(right - 10, y + 5))
        view = QRectF(outer.left(), outer.top() + TITLEBAR, outer.width(), outer.height() - TITLEBAR)
        base = view.width() / shot.width()
        p.drawImage(QRectF(view.left(), view.top(), shot.width() * base, shot.height() * base), shot)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(rounded(outer.adjusted(.5, .5, -.5, -.5), 14))
        p.restore()
        # Converte coordenadas da interface para a tela, já com a aproximação.
        self.transform = (center.x() + (view.left() - center.x()) * z,
                          center.y() + (view.top() - center.y()) * z, base * z)

    def to_screen(self, point: QPointF) -> QPointF:
        x, y, scale = self.transform
        return QPointF(x + point.x() * scale, y + point.y() * scale)

    def draw_cursor(self, p: QPainter, click: float | None) -> None:
        point = self.to_screen(self.cursor)
        if click is not None:
            radius = 10 + 26 * ease_out(click)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(201, 169, 107, int(120 * (1 - click))))
            p.drawEllipse(point, radius, radius)
        size = 1.25
        shape = QPolygonF([QPointF(0, 0), QPointF(0, 17), QPointF(4.2, 13), QPointF(7.2, 19.5), QPointF(9.8, 18.4),
                           QPointF(6.9, 12.1), QPointF(12.4, 12.1)])
        shape = QPolygonF([point + QPointF(item.x() * size, item.y() * size) for item in shape])
        p.setPen(QPen(QColor("#111111"), 1.4))
        p.setBrush(QColor("#FFFFFF"))
        p.drawPolygon(shape)

    def draw_toast(self, p: QPainter, message: str, t: float) -> None:
        k = ease_out(min(1, (t - 6.35) / .4))
        rect = QRectF(FRAME.center().x() - 140, FRAME.top() + 62 - (1 - k) * 18, 280, 48)
        p.save()
        p.setOpacity(k)
        shadow(p, rect, 12, 18, 9)
        p.setPen(QPen(QColor("#23392A"), 1))
        p.setBrush(QColor("#13201A"))
        p.drawPath(rounded(rect, 12))
        p.drawPixmap(int(rect.left() + 20), int(rect.center().y() - 9), pixmap("check", theme.SUCCESS, 18))
        text(p, (rect.left() + 50, rect.top(), 220, rect.height()), message, 16, theme.SUCCESS, QFont.Weight.DemiBold,
             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        p.restore()

    def draw_caption(self, p: QPainter, scene: int, t: float) -> None:
        duration, eyebrow, title, body, *_ = SCENES[scene]
        k = ease_out(min(1, (t - .15) / .6))
        out = 1 - ease(max(0, (t - (duration - .45)) / .4))
        alpha = k * out
        shift = (1 - k) * 22
        p.save()
        p.setOpacity(alpha)
        text(p, (96, 300 + shift, 460, 30), f"{scene:02d}   {eyebrow}", 15, theme.GOLD, QFont.Weight.DemiBold, spacing=2.4)
        p.fillRect(QRectF(96, 342 + shift, 36 * k, 2), QColor(theme.GOLD))
        text(p, (92, 372 + shift, 480, 200), title, 48, theme.TEXT, QFont.Weight.DemiBold, spacing=-.6)
        text(p, (96, 520 + shift * 1.4, 440, 160), body, 22, theme.TEXT_2)
        p.restore()

    def draw_chrome(self, p: QPainter, absolute: float) -> None:
        text(p, (96, 64, 600, 30), "STUDIO FD PERFORMANCE", 15, theme.TEXT_2, QFont.Weight.DemiBold, spacing=3.2)
        text(p, (96, 1000, 900, 30), "Protótipo em desenvolvimento  ·  dados fictícios  ·  telas reais do aplicativo", 14, "#55544F")
        p.fillRect(QRectF(0, H - 3, W * absolute / DURATION, 3), QColor(theme.GOLD))

    def draw_intro(self, p: QPainter, t: float, outro: bool = False) -> None:
        k = ease_out(min(1, t / 1.1))
        p.save()
        p.setOpacity(k)
        mark = QRectF(W / 2 - 52, 300 - (1 - k) * 20, 104, 104)
        p.setPen(QPen(QColor(theme.GOLD_LINE), 1.5))
        p.setBrush(QColor(theme.GOLD_TINT))
        p.drawPath(rounded(mark, 26))
        text(p, (mark.left(), mark.top() - 4, mark.width(), mark.height()), "FD", 50, theme.GOLD,
             align=Qt.AlignmentFlag.AlignCenter, family="Georgia")
        p.restore()
        k2 = ease_out(min(1, max(0, t - .35) / 1.0))
        p.save()
        p.setOpacity(k2)
        text(p, (0, 440 + (1 - k2) * 16, W, 40), "S T U D I O   F D   P E R F O R M A N C E", 18, theme.GOLD,
             QFont.Weight.DemiBold, Qt.AlignmentFlag.AlignHCenter)
        headline = "Pronto para o próximo passo?" if outro else "O sistema do seu Studio."
        text(p, (0, 492 + (1 - k2) * 22, W, 90), headline, 64, theme.TEXT, QFont.Weight.DemiBold, Qt.AlignmentFlag.AlignHCenter, spacing=-1)
        p.restore()
        k3 = ease_out(min(1, max(0, t - 1.0) / 1.0))
        p.save()
        p.setOpacity(k3)
        sub = ("Uma primeira versão feita para Andradina, pronta para evoluir com vocês."
               if outro else "Alunos, planos e atendimento. Feito sob medida para o atendimento personalizado.")
        text(p, (0, 600, W, 40), sub, 24, theme.TEXT_2, align=Qt.AlignmentFlag.AlignHCenter)
        p.restore()
        if outro:
            k4 = ease_out(min(1, max(0, t - 1.6) / .9))
            p.save()
            p.setOpacity(k4)
            pill = QRectF(W / 2 - 190, 690, 380, 54)
            p.setPen(QPen(QColor(theme.GOLD), 1.2))
            p.setBrush(QColor(theme.GOLD_TINT))
            p.drawPath(rounded(pill, 27))
            text(p, (pill.left(), pill.top(), pill.width(), pill.height()), "Vamos marcar uma demonstração", 19, theme.GOLD,
                 QFont.Weight.DemiBold, Qt.AlignmentFlag.AlignCenter)
            p.restore()

    def draw_roadmap(self, p: QPainter, t: float) -> None:
        k = ease_out(min(1, t / .8))
        p.save()
        p.setOpacity(k)
        text(p, (0, 210 + (1 - k) * 16, W, 30), "PRÓXIMAS ETAPAS", 16, theme.GOLD, QFont.Weight.DemiBold,
             Qt.AlignmentFlag.AlignHCenter, spacing=3)
        text(p, (0, 252 + (1 - k) * 20, W, 80), "O que vem a seguir.", 56, theme.TEXT, QFont.Weight.DemiBold,
             Qt.AlignmentFlag.AlignHCenter, spacing=-.8)
        p.restore()
        items = [("calendar", "Agenda", "Dois personais lado a lado\ne limite de 2 alunos por horário."),
                 ("wallet", "Financeiro", "Mensalidades, pagamentos\ne avisos de atraso."),
                 ("file", "Contratos", "PDF anexado à ficha\ne aberto com um clique."),
                 ("database", "Backup", "Um arquivo com todos os dados,\npara trocar de computador tranquilo.")]
        width, gap = 360, 28
        left = (W - (4 * width + 3 * gap)) / 2
        for index, (name, title, body) in enumerate(items):
            k_item = ease_out(min(1, max(0, t - .5 - index * .18) / .7))
            rect = QRectF(left + index * (width + gap), 420 + (1 - k_item) * 30, width, 300)
            p.save()
            p.setOpacity(k_item)
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.setBrush(QColor(theme.SURFACE))
            p.drawPath(rounded(rect, 18))
            tile = QRectF(rect.left() + 32, rect.top() + 34, 58, 58)
            p.setPen(QPen(QColor(theme.GOLD_LINE), 1))
            p.setBrush(QColor(theme.GOLD_TINT))
            p.drawPath(rounded(tile, 14))
            p.drawPixmap(int(tile.left() + 16), int(tile.top() + 16), pixmap(name, theme.GOLD, 26))
            text(p, (rect.left() + 32, rect.top() + 124, width - 64, 40), title, 28, theme.TEXT, QFont.Weight.DemiBold)
            text(p, (rect.left() + 32, rect.top() + 172, width - 60, 100), body, 19, theme.TEXT_2)
            p.restore()

    def render(self, scene: int, t: float, absolute: float) -> QImage:
        if scene != self.scene:
            self.previous = self.last
            self.enter(scene)
        image = QImage(W, H, QImage.Format.Format_RGB888)
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.background(p, absolute)
        if scene == 0:
            self.draw_intro(p, t)
        elif scene == len(SCENES) - 1:
            self.draw_intro(p, t, outro=True)
        elif scene == len(SCENES) - 2:
            self.draw_roadmap(p, t)
            self.draw_chrome(p, absolute)
        else:
            shot, click, toast, cursor = self.app_shot(scene, t)
            self.draw_window(p, shot, scene, t, 1.0)
            if cursor:
                self.draw_cursor(p, click)
            if toast:
                self.draw_toast(p, toast, t)
            self.draw_caption(p, scene, t)
            self.draw_chrome(p, absolute)
        if self.previous is not None and t < .45:
            p.setOpacity(1 - ease(t / .45))
            p.drawImage(0, 0, self.previous)
            p.setOpacity(1)
        fade_in = min(1, absolute / .8)
        fade_out = min(1, max(0, DURATION - absolute) / 1.2)
        level = min(fade_in, fade_out)
        if level < 1:
            p.fillRect(QRectF(0, 0, W, H), QColor(0, 0, 0, round(255 * (1 - level))))
        p.end()
        self.last = image
        return image

    def close(self) -> None:
        self.close_dialog()
        self.window.close()
        self.engine.dispose()


def timeline():
    offset = 0.0
    for index, scene in enumerate(SCENES):
        yield index, offset, scene[0]
        offset += scene[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", action="store_true", help="Gera apenas um quadro de cada cena")
    args = parser.parse_args()
    destination = PROJECT / "apresentacao"
    destination.mkdir(exist_ok=True)
    staging = PROJECT / "build/trailer"
    staging.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for path in [*fonts.glob("segoeui*.ttf"), fonts / "seguisb.ttf", fonts / "georgia.ttf"]:
        QFontDatabase.addApplicationFont(str(path))
    app.setStyle("Fusion")
    app.setFont(font(13))
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    apply_palette(app)
    app.setStyleSheet(STYLESHEET)

    with TemporaryDirectory(prefix="studio-trailer-", dir=staging) as directory:
        paths = AppPaths(Path(directory))
        paths.ensure_directories()
        trailer = Trailer(app, paths)
        try:
            if args.preview:
                for index, offset, duration in timeline():
                    # percorre a cena para que o estado da interface avance como no vídeo
                    for step in range(int(duration * 4)):
                        frame = trailer.render(index, step / 4, offset + step / 4)
                    frame.save(str(staging / f"preview-{index}.png"))
                print(staging, flush=True)
                return
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            music = staging / "trilha-original.wav"
            print("Preparando trilha instrumental...", flush=True)
            soundtrack(music)
            output = destination / "Studio-FD-Performance-Trailer.mp4"
            temporary = staging / "trailer-render.mp4"
            command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0", "-i", str(music),
                       "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                       "-tune", "animation", "-maxrate", "4500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(temporary)]
            with (staging / "render.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log, stdout=subprocess.DEVNULL,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                try:
                    for index, offset, duration in timeline():
                        print(f"Cena {index + 1}/{len(SCENES)}...", flush=True)
                        frames = int(round(duration * FPS))
                        for number in range(frames):
                            elapsed = number / FPS
                            frame = trailer.render(index, elapsed, offset + elapsed)
                            if number == int(frames * .75):
                                frame.save(str(staging / f"preview-{index}.png"))
                            process.stdin.write(frame.constBits())
                    process.stdin.close()
                    if process.wait(timeout=300) != 0:
                        raise RuntimeError("O codificador falhou; consulte build/trailer/render.log")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            temporary.replace(output)
            (destination / "Sobre-o-video.txt").write_text(
                f"Studio FD Performance — trailer do protótipo\nDuração: {DURATION:.0f} segundos.\n"
                f"Formato: MP4, H.264, {W}x{H}, {FPS} fps, áudio AAC.\n"
                "Telas reais do aplicativo, operadas por um roteiro automatizado com banco temporário e dados fictícios.\n"
                "Pesquisa, ficha e cadastro acontecem de verdade no banco de demonstração.\n"
                "Nenhuma conversa externa foi aberta ou mensagem enviada.\n"
                "Trilha instrumental sintetizada para o vídeo, sem gravações de terceiros. Sem narração.\n",
                encoding="utf-8-sig")
            print(json.dumps({"file": str(output), "seconds": DURATION, "bytes": output.stat().st_size}), flush=True)
        finally:
            trailer.close()


if __name__ == "__main__":
    main()
