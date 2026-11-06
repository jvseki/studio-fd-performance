"""Vídeo de apresentação da versão 0.3 com a interface real e dados fictícios.

Fluxo:
1. Abre o Studio em modo invisível (offscreen, escala 2x para nitidez),
   com um banco temporário preenchido com dados de demonstração.
2. Fotografa cada tela em momentos-chave (antes/depois de uma ação real).
3. Monta os quadros com movimento de câmera lento, legendas e transições.
4. Gera uma trilha instrumental original e codifica em MP4 (H.264 + AAC).

Requer build/video-tools com imageio-ffmpeg e numpy. Não toca no banco real,
não abre o WhatsApp e não envia nada.

Uso:  .venv\\Scripts\\python.exe tools\\create_presentation_video.py [--preview]
"""

import argparse
from datetime import date, datetime, time as clock, timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import wave

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "build/video-tools"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"

import numpy as np  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

W, H, FPS = 1920, 1080, 30
GOLD = QColor("#C9A96B")
BG = QColor("#0A0A0C")
XFADE = 0.8  # segundos de transição entre cenas (metade saída, metade entrada)
OVERLAYS = {"agenda_limit", "palette", "profile", "finance_paid"}


# ----------------------------------------------------------------------------
# Tempo falso: a demonstração acontece às 9h20 de hoje.
class MorningClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.combine(date.today(), clock(9, 20))


def settle(app, ms: int) -> None:
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


# ----------------------------------------------------------------------------
# Captura das telas
def capture(app) -> dict[str, QImage]:
    import studio_fd.views.agenda as agenda_module
    import studio_fd.views.dashboard as dashboard_module
    import studio_fd.views.student_profile as profile_module
    agenda_module.datetime = MorningClock
    dashboard_module.datetime = MorningClock
    profile_module.fit_dialog = lambda _dialog: None  # a tela offscreen é pequena; não encolher a ficha

    from studio_fd.database.migrations import migrate_database
    from studio_fd.database.session import create_database_engine, create_session_factory
    from studio_fd.services.dashboard_service import DashboardService
    from studio_fd.services.plan_service import PlanService
    from studio_fd.services.records import CashInput, PlanInput, StudentInput
    from studio_fd.services.settings_service import SettingsService
    from studio_fd.services.student_service import StudentService
    from studio_fd.utils.paths import AppPaths
    from studio_fd.views.main_window import MainWindow, ICONS, MODULES
    from studio_fd.views.student_profile import StudentProfile
    from studio_fd.widgets.motion import toast
    from studio_fd.widgets.palette import CommandPalette

    shots: dict[str, QImage] = {}
    staging = PROJECT / "build/trailer"
    staging.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="demo-", dir=staging) as directory:
        paths = AppPaths(Path(directory))
        paths.ensure_directories()
        engine = create_database_engine(paths.database)
        migrate_database(engine)
        sessions = create_session_factory(engine)
        plans, students = PlanService(sessions), StudentService(sessions)
        settings = SettingsService(sessions)
        settings.save_trainer("Douglas", True, 1)
        settings.save_trainer("Fernanda", True, 2)
        p3 = plans.save(PlanInput("Performance 3x", 3, 45000, 1, "Acompanhamento três vezes por semana"))
        p2 = plans.save(PlanInput("Essencial 2x", 2, 32000, 1))
        p5 = plans.save(PlanInput("Intensivo 5x", 5, 69000, 1))
        names = ["Ana Beatriz Souza", "Bruno Carvalho", "Carla Mendes", "Diego Ramos", "Eduarda Lima",
                 "Felipe Nogueira", "Gabriela Rocha", "Henrique Alves", "Isabela Torres", "João Pedro Martins",
                 "Juliana Santos", "Lucas Ferreira", "Mariana Prado", "Rafael Duarte"]
        ids = []
        for index, name in enumerate(names):
            plan = (p3, p2, p5)[index % 3]
            ids.append(students.save(StudentInput(
                name, "18997%06d" % index, plan_id=plan.id, monthly_fee_cents=plan.price_cents,
                due_day=(5, 10, 15)[index % 3], trainer_id=1 + index % 2, starts_on=date.today() - timedelta(days=210),
                notes="Prefere treinos no início da manhã." if index == 0 else None)).id)
        window = MainWindow(DashboardService(sessions), paths, students, plans)
        agenda, finance, cash = window.agenda_service, window.finance_service, window.cash_service
        today = date.today()
        booking = [("06:00", [0, 1]), ("07:00", [2, 3]), ("08:00", [4]), ("09:00", [5, 6]), ("10:00", [7]),
                   ("17:00", [8, 9]), ("18:00", [10, 11]), ("19:00", [12, 13]), ("20:00", [0])]
        for start, people in booking:
            for person in people:
                agenda.book(ids[person], today - timedelta(days=7), start, repeat_weeks=3)
        for _trainer, item in agenda.day(today)[0].cells:
            agenda.set_status(item.id, "concluido")
        first = agenda.day(today)[1].cells[0][1]
        agenda.set_status(first.id, "concluido")
        for back in range(1, 7):
            for _trainer, item in agenda.day(today - timedelta(days=back))[0].cells:
                if item:
                    agenda.set_status(item.id, "concluido" if back % 3 else "falta")

        month = today.replace(day=1)
        for offset in range(5, 0, -1):
            past = (month - timedelta(days=28 * offset)).replace(day=1)
            finance.generate(past)
            for index, record in enumerate(finance.month(past)):
                if index % 7 != 6 or offset > 1:
                    finance.register(record.id, record.due_date, ("Pix", "Dinheiro", "Débito", "Crédito")[index % 4])
            cash.add(CashInput(past.replace(day=5), "Aluguel do espaço", "Aluguel", "saida", 250000, "Pix"))
            cash.add(CashInput(past.replace(day=12), "Conta de energia", "Energia", "saida", 36000 + offset * 900, "Pix"))
        finance.generate(month)
        for index, record in enumerate(finance.month(month)):
            if record.due_date <= today and index % 3 != 2:
                finance.register(record.id, record.due_date, "Pix")
        cash.add(CashInput(today, "Avaliação física · Mariana", "Avaliação", "entrada", 12000, "Pix"))
        cash.add(CashInput(today, "Material de limpeza", "Limpeza", "saida", 8650, "Dinheiro"))
        cash.add(CashInput(today - timedelta(days=2), "Manutenção do leg press", "Manutenção", "saida", 42000, "Pix"))
        pdf = Path(directory) / "contrato.pdf"
        pdf.write_bytes(b"%PDF-1.4 demonstracao")
        window.contract_service.add(ids[0], "presencial", today - timedelta(days=60), pdf, "Via original arquivada")
        window.contract_service.add(ids[1], "online", today - timedelta(days=21), pdf)
        window.backup_service.auto_backup()

        window.resize(1600, 1000)
        window.show()
        settle(app, 600)

        def page(index: int, wait: int = 700) -> QImage:
            window.go(index)
            settle(app, wait)
            return window.grab().toImage()

        shots["dashboard"] = page(0)
        shots["agenda"] = page(1, 900)
        try:
            agenda.book(ids[8], today, "07:00")
        except ValueError as error:
            toast(window, str(error), "error")
        settle(app, 650)
        shots["agenda_limit"] = window.grab().toImage()
        settle(app, 3600)

        window.go(2)
        settle(app, 700)
        shots["students"] = window.grab().toImage()
        entries = [(title, f"Ir para · {detail}", ICONS[i], None) for i, (title, detail) in enumerate(MODULES)]
        entries += [(student.full_name, "Abrir ficha", "user", None) for student in students.list()]
        palette = CommandPalette(entries, window)
        palette.show()
        palette.search.setText("ana")
        settle(app, 300)
        shots["palette"] = overlay(window.grab().toImage(), palette.grab().toImage(), top=96, dim=0.45)
        palette.close()
        profile = StudentProfile(ids[0], students, plans, window, extras=window)
        profile.resize(820, 880)
        profile.show()
        settle(app, 400)
        shots["profile"] = overlay(window.grab().toImage(), profile.grab().toImage(), top=60, dim=0.6)
        profile.close()

        shots["finance"] = page(4, 900)
        pending = next(record for record in finance.month(month) if record.status != "Pago")
        finance.register(pending.id, today, "Pix")
        window.finance.refresh()
        toast(window, f"Pagamento de {pending.student_name} registrado")
        settle(app, 650)
        shots["finance_paid"] = window.grab().toImage()
        settle(app, 3600)
        shots["cash"] = page(5)
        shots["reports"] = page(7, 1300)
        shots["backup"] = page(8)
        window.close()
        engine.dispose()
    return shots


def overlay(base: QImage, top_image: QImage, top: int, dim: float) -> QImage:
    """Diálogo centralizado sobre a janela escurecida, com sombra suave."""
    result = base.copy()
    top_image = top_image.copy()
    result.setDevicePixelRatio(1)  # coordenadas em pixels reais nas duas imagens
    top_image.setDevicePixelRatio(1)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillRect(result.rect(), QColor(0, 0, 0, int(255 * dim)))
    x = (result.width() - top_image.width()) / 2
    y = top * 2
    for spread in range(40, 0, -4):
        path = QPainterPath()
        path.addRoundedRect(QRectF(x - spread, y - spread + 16, top_image.width() + 2 * spread, top_image.height() + 2 * spread), 40, 40)
        painter.fillPath(path, QColor(0, 0, 0, 10))
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(x, y, top_image.width(), top_image.height()), 24, 24)
    painter.setClipPath(clip)
    painter.drawImage(QPointF(x, y), top_image)
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#33302A"), 2))
    painter.drawPath(clip)
    painter.end()
    return result


# ----------------------------------------------------------------------------
# Roteiro: (duração, chave da cena, legenda pequena, título, complemento, keyframes, foco/zoom)
def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def out_cubic(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


SCENES = [
    dict(kind="title", seconds=4.6),
    dict(kind="shot", seconds=6.0, eyebrow="VISÃO GERAL", title="O dia do Studio em uma tela.",
         detail="Alunos, agenda de hoje, recebimentos e atrasos.",
         frames=[(0, "dashboard")], focus=(0.5, 0.5), zoom=(1.0, 1.08)),
    dict(kind="shot", seconds=8.0, eyebrow="AGENDA", title="Dois personais. Dois alunos por horário.",
         detail="Ao tentar um terceiro, o sistema bloqueia.",
         frames=[(0, "agenda"), (4.0, "agenda_limit")], focus=(0.62, 0.62), zoom=(1.0, 1.12)),
    dict(kind="shot", seconds=7.5, eyebrow="ALUNOS", title="Qualquer aluno a um atalho de distância.",
         detail="Ctrl+K, digite o nome e a ficha abre.",
         frames=[(0, "students"), (1.8, "palette"), (4.2, "profile")], focus=(0.5, 0.45), zoom=(1.0, 1.06)),
    dict(kind="shot", seconds=7.5, eyebrow="FINANCEIRO", title="Mensalidades em dia, sem planilha.",
         detail="O pagamento registrado já entra no caixa.",
         frames=[(0, "finance"), (3.6, "finance_paid")], focus=(0.6, 0.55), zoom=(1.0, 1.08)),
    dict(kind="shot", seconds=7.0, eyebrow="CAIXA E RELATÓRIOS", title="Entradas, saídas e o resultado do mês.",
         detail="Gráfico dos últimos seis meses.",
         frames=[(0, "cash"), (3.2, "reports")], focus=(0.55, 0.5), zoom=(1.0, 1.06)),
    dict(kind="shot", seconds=6.0, eyebrow="SEGURANÇA", title="Backup completo em um único arquivo.",
         detail="Troque de computador sem perder nenhum dado.",
         frames=[(0, "backup")], focus=(0.5, 0.35), zoom=(1.0, 1.08)),
    dict(kind="end", seconds=5.6),
]
starts = []
cursor = 0.0
for scene in SCENES:
    starts.append(cursor)
    cursor += scene["seconds"] - XFADE
DURATION = cursor + XFADE


def font(size: float, weight=QFont.Weight.Normal, family="Segoe UI", spacing: float = 0) -> QFont:
    result = QFont(family)
    result.setPixelSize(int(size))
    result.setWeight(weight)
    if spacing:
        result.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return result


def draw_text(painter, rect, text, size, color, weight=QFont.Weight.Normal, align=Qt.AlignmentFlag.AlignLeft, spacing=0, opacity=1.0):
    painter.save()
    painter.setOpacity(opacity)
    painter.setFont(font(size, weight, spacing=spacing))
    painter.setPen(QColor(color))
    painter.drawText(QRectF(*rect), align | Qt.AlignmentFlag.AlignVCenter, text)
    painter.restore()


def background(painter: QPainter, t: float) -> None:
    painter.fillRect(QRectF(0, 0, W, H), BG)
    glow = QRadialGradient(QPointF(W * 0.72 + 60 * math.sin(t / 7), -120), 1300)
    glow.setColorAt(0, QColor(201, 169, 107, 26))
    glow.setColorAt(1, QColor(201, 169, 107, 0))
    painter.fillRect(QRectF(0, 0, W, H), glow)


def wordmark(painter: QPainter, t: float, closing: bool) -> None:
    reveal = out_cubic(t / 1.4)
    painter.save()
    painter.setOpacity(reveal)
    draw_text(painter, (0, 400 - 14 * (1 - reveal), W, 90), "STUDIO  FD", 74, "#F2F0EB", QFont.Weight.Light,
              Qt.AlignmentFlag.AlignHCenter, spacing=14)
    line = 260 * out_cubic((t - 0.5) / 1.2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(GOLD)
    painter.drawRect(QRectF(W / 2 - line / 2, 506, line, 1.5))
    draw_text(painter, (0, 528, W, 40), "PERFORMANCE", 20, GOLD.name(), QFont.Weight.DemiBold,
              Qt.AlignmentFlag.AlignHCenter, spacing=9, opacity=ease((t - 0.9) / 0.8))
    if closing:
        draw_text(painter, (0, 650, W, 44), "Um sistema feito para a rotina do Studio.", 30, "#D9D6CF",
                  QFont.Weight.Light, Qt.AlignmentFlag.AlignHCenter, opacity=ease((t - 1.4) / 0.9))
        draw_text(painter, (0, 704, W, 34), "Agenda  ·  Alunos  ·  Financeiro  ·  Caixa  ·  Contratos  ·  Backup", 19,
                  "#8E8B84", align=Qt.AlignmentFlag.AlignHCenter, spacing=1, opacity=ease((t - 2.0) / 0.9))
    else:
        draw_text(painter, (0, 650, W, 40), "Versão 0.3  ·  apresentação do sistema", 22, "#8E8B84",
                  QFont.Weight.Light, Qt.AlignmentFlag.AlignHCenter, spacing=1, opacity=ease((t - 1.6) / 0.9))
    painter.restore()


def screenshot_scene(painter: QPainter, scene: dict, t: float, shots: dict[str, QImage]) -> None:
    progress = t / scene["seconds"]
    zoom = scene["zoom"][0] + (scene["zoom"][1] - scene["zoom"][0]) * ease(progress)
    # Cartão-base: a janela inteira com margem; a câmera aproxima devagar do foco.
    base_w = 1600
    base_h = 1000
    fit = 0.95 * min(W / base_w, (H - 40) / base_h)
    card = QRectF(-base_w / 2, -base_h / 2, base_w, base_h)
    fx = (scene["focus"][0] - 0.5) * base_w * ease(progress)
    fy = (scene["focus"][1] - 0.5) * base_h * ease(progress)
    rise = 26 * (1 - out_cubic(t / 1.1))
    painter.save()
    painter.translate(W / 2, H / 2 + 6 + rise)
    painter.scale(fit * zoom, fit * zoom)
    painter.translate(-fx * 0.22, -fy * 0.22)  # desliza levemente em direção ao foco
    for spread in range(60, 0, -6):
        shadow = QPainterPath()
        shadow.addRoundedRect(card.adjusted(-spread, -spread + 24, spread, spread + 24), 22 + spread, 22 + spread)
        painter.fillPath(shadow, QColor(0, 0, 0, 9))
    clip = QPainterPath()
    clip.addRoundedRect(card, 14, 14)
    painter.setClipPath(clip)
    frames = scene["frames"]
    current = max(index for index, (start, _key) in enumerate(frames) if t >= start or index == 0)
    start, key = frames[current]
    if current == 0:
        painter.drawImage(card, shots[key])
    elif key in OVERLAYS:
        # Mesma tela por baixo (aviso, busca, ficha): fusão suave.
        painter.drawImage(card, shots[frames[current - 1][1]])
        painter.setOpacity(ease((t - start) / 0.45))
        painter.drawImage(card, shots[key])
    else:
        # Tela diferente: a anterior escurece e a nova surge, sem sobreposição.
        local = t - start
        if local < 0.22:
            painter.setOpacity(1 - ease(local / 0.22))
            painter.drawImage(card, shots[frames[current - 1][1]])
        else:
            painter.setOpacity(ease((local - 0.22) / 0.32))
            painter.drawImage(card, shots[key])
    painter.setOpacity(1)
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#2E2B25"), 1.2 / (fit * zoom)))
    painter.drawPath(clip)
    painter.restore()

    # Faixa de legenda: degradê na base e texto que sobe suavemente.
    painter.drawImage(0, H - 360, SCRIM)
    appear = out_cubic((t - 0.45) / 0.9)
    shift = 18 * (1 - appear)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(GOLD)
    painter.setOpacity(appear)
    painter.drawRect(QRectF(120, H - 196 + shift, 34 * appear, 2))
    painter.setOpacity(1)
    draw_text(painter, (170, H - 210 + shift, 900, 30), scene["eyebrow"], 17, GOLD.name(), QFont.Weight.DemiBold, spacing=4, opacity=appear)
    draw_text(painter, (118, H - 172 + shift, 1700, 70), scene["title"], 50, "#F4F2ED", QFont.Weight.Light, opacity=appear)
    detail_appear = out_cubic((t - 0.85) / 0.9)
    draw_text(painter, (120, H - 104 + 12 * (1 - detail_appear), 1600, 40), scene["detail"], 24, "#A9A6A0",
              opacity=detail_appear)


def make_scrim() -> QImage:
    """Degradê escuro sob a legenda: forte à esquerda, some antes do canto direito
    (onde aparecem os avisos do sistema)."""
    image = QImage(W, 360, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    vertical = QLinearGradient(0, 0, 0, 360)
    vertical.setColorAt(0, QColor(10, 10, 12, 0))
    vertical.setColorAt(0.55, QColor(10, 10, 12, 220))
    vertical.setColorAt(1, QColor(10, 10, 12, 245))
    painter.fillRect(image.rect(), vertical)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    horizontal = QLinearGradient(0, 0, W, 0)
    horizontal.setColorAt(0, QColor(0, 0, 0, 255))
    horizontal.setColorAt(0.5, QColor(0, 0, 0, 255))
    horizontal.setColorAt(0.7, QColor(0, 0, 0, 0))
    painter.fillRect(image.rect(), horizontal)
    painter.end()
    return image


SCRIM = None


def render_scene(painter: QPainter, index: int, t: float, shots) -> None:
    scene = SCENES[index]
    if scene["kind"] in ("title", "end"):
        wordmark(painter, t, closing=scene["kind"] == "end")
    else:
        screenshot_scene(painter, scene, t, shots)


def frame_at(absolute: float, shots) -> QImage:
    image = QImage(W, H, QImage.Format.Format_RGB888)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    background(painter, absolute)
    active = [i for i, start in enumerate(starts) if start <= absolute < start + SCENES[i]["seconds"]]
    for position, index in enumerate(active):
        local = absolute - starts[index]
        if len(active) == 1:
            painter.setOpacity(1.0)
        elif position == 0:
            # cena que sai: some na primeira metade da transição
            following = absolute - starts[active[1]]
            painter.setOpacity(1 - ease(following / (XFADE / 2)))
        else:
            painter.setOpacity(ease((local - XFADE / 2) / (XFADE / 2)))
        layer = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
        layer.fill(Qt.GlobalColor.transparent)
        layer_painter = QPainter(layer)
        layer_painter.setRenderHints(painter.renderHints())
        render_scene(layer_painter, index, local, shots)
        layer_painter.end()
        fade_out = 1.0
        if index == len(SCENES) - 1:
            fade_out = 1 - ease((local - (SCENES[index]["seconds"] - 1.2)) / 1.2)
        if index == 0:
            fade_out *= ease(local / 0.6)
        painter.setOpacity(painter.opacity() * fade_out)
        painter.drawImage(0, 0, layer)
    painter.end()
    return image


# ----------------------------------------------------------------------------
# Trilha original: pad quente, piano suave e reverberação simples.
def soundtrack(path: Path) -> None:
    rate = 44100
    total = int((DURATION + 0.5) * rate)
    t = np.arange(total) / rate
    beat = 60 / 76
    note = lambda name: 440 * 2 ** ((name - 69) / 12)
    # Dmaj9 – Bm7 – Gmaj7 – A6sus (MIDI)
    chords = [[50, 57, 62, 66, 69, 76], [47, 54, 62, 66, 69, 73], [43, 55, 59, 62, 66, 71], [45, 52, 57, 62, 64, 69]]
    bar = beat * 4
    left = np.zeros(total)
    right = np.zeros(total)
    for start_bar in range(int(DURATION / bar) + 2):
        chord = chords[start_bar % 4]
        start = start_bar * bar
        a, b = int(start * rate), min(total, int((start + bar + 1.6) * rate))
        if a >= total:
            break
        local = t[a:b] - start
        env = np.minimum(1, local / 1.1) * np.clip((bar + 1.6 - local) / 1.6, 0, 1)
        for index, midi in enumerate(chord):
            freq = note(midi)
            for detune, pan in ((0.9985, 0.75), (1.0015, 0.25)):
                tone = np.sin(2 * np.pi * freq * detune * t[a:b]) + 0.18 * np.sin(4 * np.pi * freq * detune * t[a:b])
                amp = 0.020 if midi > 60 else 0.026
                left[a:b] += tone * env * amp * pan
                right[a:b] += tone * env * amp * (1 - pan)
        root = note(chord[0] - 12)
        bass = np.sin(2 * np.pi * root * t[a:b]) * env * 0.05
        left[a:b] += bass
        right[a:b] += bass
        # Piano: arpejo leve a cada batida e meia
        pattern = [chord[3] + 12, chord[4] + 12, chord[2] + 12, chord[5] + 12 if start_bar % 2 else chord[4] + 12]
        for step, midi in enumerate(pattern):
            onset = start + step * beat * 1.0 + (0.5 * beat if step == 3 else 0)
            c, d = int(onset * rate), min(total, int((onset + 3.2) * rate))
            if c >= total:
                continue
            local = t[c:d] - onset
            freq = note(midi)
            decay = np.exp(-local * 1.6) * np.minimum(1, local / 0.006)
            tone = (np.sin(2 * np.pi * freq * local) + 0.35 * np.sin(4 * np.pi * freq * local) * np.exp(-local * 3)
                    + 0.12 * np.sin(6 * np.pi * freq * local) * np.exp(-local * 5))
            pan = 0.35 + 0.3 * (step % 2)
            left[c:d] += tone * decay * 0.045 * (1 - pan) * 2
            right[c:d] += tone * decay * 0.045 * pan * 2
    # "Respiro" de ar nas trocas de cena
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(total)
    smooth = np.convolve(noise, np.ones(40) / 40, mode="same")
    for start in starts[1:]:
        a, b = int((start - 0.9) * rate), int((start + 0.5) * rate)
        a, b = max(0, a), min(total, b)
        local = (t[a:b] - (start - 0.9)) / 1.4
        swell = np.sin(np.pi * np.clip(local, 0, 1)) ** 2 * 0.05
        left[a:b] += smooth[a:b] * swell
        right[a:b] += smooth[a:b][::-1] * swell
    # Reverberação: ecos curtos decrescentes e eco estéreo
    for delay, gain in ((0.029, 0.32), (0.043, 0.28), (0.067, 0.24), (0.101, 0.2), (0.149, 0.16), (0.211, 0.12)):
        shift = int(delay * rate)
        left[shift:] += left[:-shift] * gain * 0.6
        right[shift:] += right[:-shift] * gain * 0.6
    echo = int(beat * 0.75 * rate)
    left[echo:] += right[:-echo] * 0.18
    right[echo:] += left[:-echo] * 0.18
    fade = np.minimum(1, t / 2.0) * np.clip((DURATION - t) / 3.0, 0, 1)
    mix = np.stack([left * fade, right * fade], axis=1)
    mix /= max(1e-9, np.abs(mix).max()) / 0.62
    data = (mix * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(data.tobytes())


# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Gera só quadros de amostra em build/trailer")
    args = parser.parse_args()
    app = QApplication([])
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "segoeuil.ttf", "segoeuisl.ttf", "georgia.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
    from studio_fd.views.theme import STYLESHEET, apply_palette
    from studio_fd.widgets.motion import install_wheel_guard
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    apply_palette(app)
    app.setStyleSheet(STYLESHEET)
    install_wheel_guard(app)
    global SCRIM
    SCRIM = make_scrim()
    staging = PROJECT / "build/trailer"
    print("Capturando telas...", flush=True)
    shots = capture(app)
    if args.preview:
        for index, start in enumerate(starts):
            moment = start + SCENES[index]["seconds"] * 0.7
            frame_at(moment, shots).save(str(staging / f"v3-preview-{index}.png"))
        print(staging, flush=True)
        return

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    music = staging / "trilha-v3.wav"
    print("Compondo trilha...", flush=True)
    soundtrack(music)
    destination = PROJECT / "apresentacao"
    destination.mkdir(exist_ok=True)
    output = destination / "Studio-FD-Performance-Apresentacao.mp4"
    temporary = staging / "apresentacao-render.mp4"
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0", "-i", str(music),
               "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
               "-maxrate", "2600k", "-bufsize", "5200k", "-pix_fmt", "yuv420p", "-profile:v", "high",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(temporary)]
    total = int(DURATION * FPS)
    with (staging / "render-v3.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log, stdout=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            for number in range(total):
                frame = frame_at(number / FPS, shots)
                process.stdin.write(bytes(frame.constBits()))
                if number % (FPS * 5) == 0:
                    print(f"{number / FPS:4.0f}s / {DURATION:.0f}s", flush=True)
            process.stdin.close()
            if process.wait(timeout=300) != 0:
                raise RuntimeError("O codificador falhou; veja build/trailer/render-v3.log")
        finally:
            if process.poll() is None:
                process.kill()
    temporary.replace(output)
    print(json.dumps({"file": str(output), "seconds": round(DURATION, 1), "bytes": output.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
