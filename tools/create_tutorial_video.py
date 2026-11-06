"""Vídeo tutorial narrado: ensina a usar todas as funções do Studio FD Performance.

Para cada passo do roteiro:
- a interface real é aberta (offscreen, escala 2x) com dados fictícios e a tela é fotografada;
- a fala é sintetizada pela voz do Windows (OneCore, offline) — tools/tts_onecore.ps1;
- o quadro mostra a tela, um cursor indo até o botão, destaque no que é explicado e legenda.

Uso:
  .venv\\Scripts\\python.exe tools\\create_tutorial_video.py            (voz Daniel)
  .venv\\Scripts\\python.exe tools\\create_tutorial_video.py --voz Maria
  .venv\\Scripts\\python.exe tools\\create_tutorial_video.py --preview  (só quadros de amostra)
"""

import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_presentation_video as base  # noqa: E402  (ajusta ambiente Qt offscreen 2x e caminhos)

import numpy as np  # noqa: E402
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen, QPolygonF  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

PROJECT = base.PROJECT
W, H, FPS = base.W, base.H, base.FPS
GOLD = base.GOLD
STAGING = PROJECT / "build/tutorial"
CARD_W, CARD_H = 1600, 1000
FIT = 0.86
CENTER = QPointF(W / 2, 26 + CARD_H * FIT / 2)
BAND_TOP = 26 + CARD_H * FIT + 12
STEP_FADE = 0.35

# ----------------------------------------------------------------------------
# Roteiro. Cada passo: capítulo, imagem, fala, alvo (nome do retângulo), clique, destaque, zoom.
CHAPTERS = ["Conhecendo a tela", "Configurações", "Planos", "Alunos", "Agenda", "Financeiro",
            "Caixa", "Contratos", "Relatórios", "Backup"]


def step(chapter, image, text, target=None, click=False, spot=False, zoom=1.0):
    return dict(kind="step", chapter=chapter, image=image, text=text, target=target, click=click, spot=spot, zoom=zoom)


def card(title, subtitle="", text=None, seconds=3.2):
    return dict(kind="card", title=title, subtitle=subtitle, text=text, seconds=seconds)


SCRIPT = [
    card("Studio FD Performance", "Tutorial completo do sistema",
         "Olá! Neste tutorial você vai aprender a usar o Studio FD Performance, passo a passo. "
         "Vamos ver como configurar o Studio, cadastrar alunos, montar a agenda, cuidar das mensalidades e do caixa, e fazer backup."),
    card("1 · Conhecendo a tela", "Dashboard, menu e atalhos", seconds=2.6),
    step(1, "dashboard", "Esta é a tela inicial, chamada Dashboard. Ela mostra o resumo do dia: alunos ativos, "
         "atendimentos marcados hoje, quanto já foi recebido no mês e as mensalidades em atraso."),
    step(1, "dashboard", "Mais abaixo aparecem os próximos vencimentos e a agenda de hoje, com os dois personais lado a lado.",
         target="dash_agenda", spot=True),
    step(1, "dashboard", "À esquerda fica o menu. Cada item abre uma parte do sistema, e o item com a barrinha dourada é a tela em que você está.",
         target="nav", spot=True),
    step(1, "dashboard", "Para ir mais rápido, use a busca. Aperte Control e K, digite o nome de um aluno ou de uma tela e tecle Enter.",
         target="search_hint", click=True, spot=True, zoom=1.35),
    step(1, "palette", "Por exemplo: digitando ana, aparecem os alunos com esse nome. É só escolher e a ficha abre na hora.",
         target="palette_box", spot=True),
    step(1, "dashboard", "Este botão recolhe o menu e deixa só os ícones, para sobrar mais espaço na tela. O atalho é Control e B.",
         target="toggle", click=True, spot=True, zoom=1.4),

    card("2 · Configurações", "Personais e horário de funcionamento", seconds=2.6),
    step(2, "settings", "Antes de começar, abra Configurações. Aqui ficam os personais do Studio. "
         "Cada personal ativo vira uma coluna na agenda.", target="nav_settings", click=True),
    step(2, "settings", "Com dois personais ativos, cada horário aceita no máximo dois alunos, um com cada personal. "
         "Para trocar um nome, edite e clique em Salvar.", target="trainers", spot=True),
    step(2, "settings", "Logo abaixo, defina a abertura, o fechamento e a duração de cada atendimento. "
         "A agenda monta os horários do dia a partir daqui.", target="hours", spot=True),

    card("3 · Planos", "Os pacotes que o Studio vende", seconds=2.6),
    step(3, "plans", "Em Planos ficam os pacotes do Studio, como duas, três ou cinco vezes por semana, cada um com o seu valor.",
         target="nav_plans", click=True),
    step(3, "plans", "Para criar um plano, clique em Novo plano.", target="new_plan", click=True, spot=True, zoom=1.3),
    step(3, "plan_dialog", "Preencha o nome, quantos treinos por semana, o valor e a duração, e clique em Salvar plano. "
         "Mudar o preço depois não altera o valor já combinado com quem já é aluno.", target="plan_form", spot=True),

    card("4 · Alunos", "Cadastro, pesquisa e ficha", seconds=2.6),
    step(4, "students", "Em Alunos fica o cadastro de todo mundo. Para incluir um aluno novo, clique em Novo aluno.",
         target="new_student", click=True, spot=True, zoom=1.3),
    step(4, "student_dialog", "Só o nome e o telefone são obrigatórios. Ao escolher o plano, o valor da mensalidade é preenchido sozinho, "
         "mas você pode ajustar o valor combinado.", target="student_plan", spot=True),
    step(4, "student_dialog", "Informe também o dia do vencimento e o personal responsável. Depois é só clicar em Salvar aluno.",
         target="student_save", click=True, spot=True),
    step(4, "students_search", "Para encontrar alguém, digite parte do nome na pesquisa. A lista filtra enquanto você digita.",
         target="search", spot=True, zoom=1.25),
    step(4, "students_letter", "Você também pode clicar numa letra, para ver só os alunos que começam com ela.",
         target="letter_j", click=True, spot=True, zoom=1.35),
    step(4, "profile", "Clicando no aluno, abre a ficha. Nela estão o plano, a mensalidade, o vencimento, os horários fixos, "
         "o histórico de pagamentos e o contrato.", target="profile_box", spot=True),
    step(4, "whatsapp", "O botão WhatsApp prepara uma mensagem para o aluno. Você revisa o texto e envia pelo seu WhatsApp. "
         "Nada é enviado sozinho.", target="whatsapp_box", spot=True),

    card("5 · Agenda", "Horários dos personais", seconds=2.6),
    step(5, "agenda", "A Agenda mostra o dia com os personais lado a lado. Cada linha é um horário, e cada cartão é uma vaga.",
         target="nav_agenda", click=True),
    step(5, "agenda", "No alto aparece a semana. A barrinha mostra quanto cada dia já está ocupado. "
         "Clique num dia para abri-lo, ou use as setas para avançar.", target="week", spot=True),
    step(5, "agenda_hover", "Para agendar, clique numa vaga livre.", target="free_slot", click=True, spot=True, zoom=1.25),
    step(5, "booking", "Escolha o aluno e confira a data, o horário e o personal. Se for um horário fixo, marque Repetir toda semana: "
         "o sistema já agenda as próximas semanas de uma vez.", target="booking_repeat", spot=True),
    step(5, "booked", "Pronto. O aluno aparece na vaga, com a situação Agendado.", target="free_slot", spot=True),
    step(5, "limit", "E se o horário já tiver dois alunos, o sistema não deixa marcar um terceiro. Ele avisa na hora.",
         target="toast", spot=True),
    step(5, "agenda_menu", "Clicando num aluno da agenda, você marca se ele compareceu, registra falta, abre a ficha ou desmarca o horário.",
         target="agenda_menu_box", spot=True),
    step(5, "agenda_status", "Os atendimentos concluídos ficam em verde e as faltas em vermelho. Essas marcações alimentam o relatório de presença.",
         target="status_rows", spot=True),

    card("6 · Financeiro", "Mensalidades e pagamentos", seconds=2.6),
    step(6, "finance_empty", "No Financeiro ficam as mensalidades. No começo de cada mês, clique em Gerar mensalidades.",
         target="generate", click=True, spot=True, zoom=1.3),
    step(6, "finance", "O sistema cria a cobrança de todos os alunos ativos, com o valor e o vencimento que estão na ficha de cada um. "
         "Cada linha mostra a situação: pendente, paga ou atrasada.", target="finance_table", spot=True),
    step(6, "finance", "Estes filtros mostram só as atrasadas, só as pendentes ou só as pagas.", target="filter", click=True, spot=True, zoom=1.3),
    step(6, "finance_menu", "Quando o aluno pagar, clique na mensalidade dele e escolha Registrar pagamento.", target="finance_menu_box", spot=True),
    step(6, "payment", "Confira o valor, a data e a forma de pagamento, e clique em Confirmar recebimento.", target="payment_form", spot=True),
    step(6, "paid", "A mensalidade passa para Paga, e o valor entra sozinho no Caixa. "
         "Se registrar por engano, clique de novo nela e escolha Desfazer pagamento.", target="paid_row", spot=True),

    card("7 · Caixa", "Entradas e saídas do Studio", seconds=2.6),
    step(7, "cash", "O Caixa mostra todo o dinheiro que entrou e saiu. Os pagamentos de mensalidade já aparecem aqui automaticamente.",
         target="nav_cash", click=True),
    step(7, "cash_dialog", "Para outras movimentações, use os botões Entrada ou Saída. Por exemplo, a conta de energia: "
         "descrição, categoria, valor e forma de pagamento.", target="cash_form", spot=True),
    step(7, "cash", "Aqui você alterna entre o dia e o mês inteiro. O saldo é sempre as entradas menos as saídas.",
         target="period", click=True, spot=True, zoom=1.3),

    card("8 · Contratos", "O PDF assinado de cada aluno", seconds=2.6),
    step(8, "contracts", "Em Contratos você guarda o contrato assinado de cada aluno. Para incluir, clique em Anexar contrato.",
         target="attach", click=True, spot=True, zoom=1.3),
    step(8, "contract_dialog", "Escolha o aluno, se foi assinado presencialmente ou online, a data e o arquivo em PDF. "
         "O arquivo é copiado para a pasta do sistema e entra no backup.", target="contract_form", spot=True),
    step(8, "contract_menu", "Para ver um contrato, clique nele e escolha Abrir contrato. O PDF abre no leitor do computador.",
         target="contract_menu_box", spot=True),

    card("9 · Relatórios", "O resultado do mês", seconds=2.6),
    step(9, "reports", "Em Relatórios você acompanha o mês: entradas, saídas, o resultado e a presença dos alunos.",
         target="report_cards", spot=True),
    step(9, "reports_hover", "O gráfico compara os últimos seis meses. Passe o mouse numa coluna para ver os valores.",
         target="chart", spot=True),

    card("10 · Backup", "Seus dados sempre seguros", seconds=2.6),
    step(10, "backup", "Agora a parte mais importante: o Backup. Ele junta alunos, pagamentos, agenda, contratos e configurações em um único arquivo.",
         target="nav_backup", click=True),
    step(10, "backup", "Clique em Exportar agora e salve o arquivo num pen drive ou na nuvem. O ideal é fazer isso pelo menos uma vez por semana.",
         target="export", click=True, spot=True, zoom=1.3),
    step(10, "backup", "Além disso, o sistema faz sozinho um backup por dia, quando é aberto, e guarda os dez mais recentes.",
         target="backup_list", spot=True),
    step(10, "backup", "Se trocar de computador, instale o Studio e use Restaurar backup. O sistema confere o arquivo, "
         "guarda uma cópia dos dados atuais e reabre com tudo de volta.", target="restore", spot=True),

    card("Pronto!", "A rotina em quatro passos",
         "Pronto! Esse é o básico do Studio. A rotina é simples: agende os alunos, gere as mensalidades no começo do mês, "
         "registre os pagamentos e faça o backup toda semana. Bom trabalho!", seconds=3.5),
]


# ----------------------------------------------------------------------------
# Captura
def rect_in(widget, window, offset=(0, 0)) -> QRectF:
    point = widget.mapTo(window, QPoint(0, 0))
    return QRectF(point.x() + offset[0], point.y() + offset[1], widget.width(), widget.height())


def button(view, text):
    return next(b for b in view.findChildren(QPushButton) if text in b.text())


def place(dialog, top=60):
    return ((CARD_W - dialog.width()) / 2, top)


def compose(base_image: QImage, top_image: QImage, x: float, y: float, dim: float = 0.0, rounded: bool = True) -> QImage:
    """Coloca um diálogo ou menu sobre a janela (coordenadas lógicas da janela)."""
    result = base_image.copy()
    piece = top_image.copy()
    result.setDevicePixelRatio(1)
    piece.setDevicePixelRatio(1)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if dim:
        painter.fillRect(result.rect(), QColor(0, 0, 0, int(255 * dim)))
    x, y = x * 2, y * 2
    for spread in range(36, 0, -4):
        path = QPainterPath()
        path.addRoundedRect(QRectF(x - spread, y - spread + 14, piece.width() + 2 * spread, piece.height() + 2 * spread), 30, 30)
        painter.fillPath(path, QColor(0, 0, 0, 9))
    if rounded:
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(x, y, piece.width(), piece.height()), 24, 24)
        painter.setClipPath(clip)
    painter.drawImage(QPointF(x, y), piece)
    if rounded:
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#33302A"), 2))
        painter.drawPath(clip)
    painter.end()
    return result


def menu_image(parent, items):
    from studio_fd.widgets.controls import styled_menu
    from studio_fd.widgets.icons import icon
    from studio_fd.views import theme
    menu = styled_menu(parent)
    for item in items:
        if item is None:
            menu.addSeparator()
        else:
            key, text, icon_name = item
            tint = theme.DANGER if key.startswith(("delete", "remove")) else theme.TEXT_2
            menu.addAction(icon(icon_name, tint, 16), text)
    menu.adjustSize()
    menu.popup(QPoint(0, 0))
    return menu


def capture(app):
    import studio_fd.views.agenda as agenda_module
    import studio_fd.views.dashboard as dashboard_module
    import studio_fd.views.student_profile as profile_module
    import studio_fd.widgets.forms as forms_module
    agenda_module.datetime = base.MorningClock
    dashboard_module.datetime = base.MorningClock
    profile_module.fit_dialog = lambda _d: None
    forms_module.fit_dialog = lambda _d: None

    from tempfile import TemporaryDirectory
    from studio_fd.database.migrations import migrate_database
    from studio_fd.database.session import create_database_engine, create_session_factory
    from studio_fd.services.dashboard_service import DashboardService
    from studio_fd.services.plan_service import PlanService
    from studio_fd.services.records import CashInput, PlanInput, StudentInput
    from studio_fd.services.settings_service import SettingsService
    from studio_fd.services.student_service import StudentService
    from studio_fd.utils.paths import AppPaths
    from studio_fd.views.agenda import BookingDialog, SlotCard
    from studio_fd.views.cash import CashDialog
    from studio_fd.views.contracts import ContractDialog
    from studio_fd.views.finance import PaymentDialog
    from studio_fd.views.main_window import ICONS, MODULES, MainWindow
    from studio_fd.views.plans import PlanDialog
    from studio_fd.views.student_form import StudentDialog
    from studio_fd.views.student_profile import StudentProfile
    from studio_fd.views.whatsapp import WhatsAppDialog
    from studio_fd.widgets.motion import Toast, toast
    from studio_fd.widgets.palette import CommandPalette

    shots: dict[str, QImage] = {}
    rects: dict[str, QRectF] = {}
    STAGING.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="demo-", dir=STAGING) as directory:
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
        p2 = plans.save(PlanInput("Essencial 2x", 2, 32000, 1, "Ideal para começar"))
        p5 = plans.save(PlanInput("Intensivo 5x", 5, 69000, 1, "Treino de segunda a sexta"))
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
        for start, people in [("06:00", [0, 1]), ("07:00", [2, 3]), ("09:00", [5, 6]), ("10:00", [7]),
                              ("17:00", [8, 9]), ("18:00", [10]), ("19:00", [12, 13])]:
            for person in people:
                agenda.book(ids[person], today - timedelta(days=7), start, repeat_weeks=3)
        for back in range(1, 8):
            for row in agenda.day(today - timedelta(days=back))[:2]:
                for _trainer, item in row.cells:
                    if item:
                        agenda.set_status(item.id, "concluido" if (back + item.id) % 4 else "falta")
        month = today.replace(day=1)
        for offset in range(5, 0, -1):
            past = (month - timedelta(days=28 * offset)).replace(day=1)
            finance.generate(past)
            for index, record in enumerate(finance.month(past)):
                if index % 7 != 6 or offset > 1:
                    finance.register(record.id, record.due_date, ("Pix", "Dinheiro", "Débito", "Crédito")[index % 4])
            cash.add(CashInput(past.replace(day=5), "Aluguel do espaço", "Aluguel", "saida", 250000, "Pix"))
            cash.add(CashInput(past.replace(day=12), "Conta de energia", "Energia", "saida", 36000 + offset * 900, "Pix"))
        cash.add(CashInput(today, "Avaliação física · Mariana", "Avaliação", "entrada", 12000, "Pix"))
        pdf = Path(directory) / "contrato.pdf"
        pdf.write_bytes(b"%PDF-1.4 demonstracao")
        window.contract_service.add(ids[0], "presencial", today - timedelta(days=60), pdf, "Via original arquivada")
        window.contract_service.add(ids[1], "online", today - timedelta(days=21), pdf)
        window.contract_service.add(ids[4], "presencial", today - timedelta(days=12), pdf)
        window.backup_service.auto_backup()
        window.resize(CARD_W, CARD_H)
        window.show()
        settle = lambda ms=650: base.settle(app, ms)
        grab = lambda: window.grab().toImage()
        settle(600)

        def nav(index):
            return rect_in(window.navigation.button(index), window)

        def go(index, wait=750):
            window.go(index)
            settle(wait)

        def clear_toasts():
            for item in window.toast_host.findChildren(Toast):
                item.deleteLater()
            settle(80)

        # Configurações
        go(9)
        shots["settings"] = grab()
        rects["nav_settings"] = nav(9)
        rects["trainers"] = rect_in(window.settings.trainer_list.parentWidget(), window)
        rects["hours"] = rect_in(window.settings.open_time.parentWidget(), window)

        # Planos
        go(3)
        shots["plans"] = grab()
        rects["nav_plans"] = nav(3)
        rects["new_plan"] = rect_in(button(window.plans, "Novo plano"), window)
        dialog = PlanDialog(plans, parent=window)
        dialog.name.setText("Funcional 2x")
        dialog.workouts.setValue(2)
        dialog.price.set_cents(28000)
        dialog.description.setPlainText("Treino funcional em dupla")
        dialog.show()
        settle(200)
        x, y = place(dialog, 90)
        shots["plan_dialog"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["plan_form"] = rect_in(dialog.name.parentWidget(), dialog, (x, y))
        dialog.close()

        # Alunos
        go(2)
        shots["students"] = grab()
        rects["new_student"] = rect_in(button(window.students, "Novo aluno"), window)
        rects["search"] = rect_in(window.students.search, window)
        dialog = StudentDialog(students, plans, parent=window)
        dialog.name.setText("Marina Prado")
        dialog.phone.setText("(18) 99812-3456")
        dialog.plan.setCurrentIndex(dialog.plan.findData(p3.id))
        dialog.apply_plan_price()
        dialog.due_day.setValue(10)
        dialog.trainer.setCurrentIndex(dialog.trainer.findData(2))
        dialog.show()
        settle(250)
        x, y = place(dialog, 70)
        shots["student_dialog"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["student_plan"] = rect_in(dialog.plan.parentWidget().parentWidget(), dialog, (x, y))
        rects["student_save"] = rect_in(dialog.save_button, dialog, (x, y))
        dialog.close()
        window.students.search.setText("ju")
        window.students.refresh()
        settle(300)
        shots["students_search"] = grab()
        window.students.search.clear()
        window.students.letters.button(10).click()
        settle(300)
        shots["students_letter"] = grab()
        rects["letter_j"] = rect_in(window.students.letters.button(10), window)
        window.students.clear_filters()
        settle(200)
        profile = StudentProfile(ids[0], students, plans, window, extras=window)
        profile.resize(820, 900)
        profile.show()
        settle(400)
        x, y = place(profile, 50)
        shots["profile"] = compose(grab(), profile.grab().toImage(), x, y, 0.6)
        rects["profile_box"] = QRectF(x, y, profile.width(), profile.height())
        profile.close()
        chat = WhatsAppDialog(students.get(ids[0]), window)
        chat.show()
        settle(200)
        x, y = place(chat, 160)
        shots["whatsapp"] = compose(grab(), chat.grab().toImage(), x, y, 0.6)
        rects["whatsapp_box"] = QRectF(x, y, chat.width(), chat.height())
        chat.close()

        # Agenda
        go(1, 900)
        shots["agenda"] = grab()
        rects["nav_agenda"] = nav(1)
        rects["week"] = rect_in(window.agenda.week, window)
        free = next(card for card in window.agenda.findChildren(SlotCard)
                    if card.item is None and card.time == "08:00" and card.trainer.id == 1)
        rects["free_slot"] = rect_in(free, window)
        free._hover = 1.0
        free.update()
        settle(120)
        shots["agenda_hover"] = grab()
        dialog = BookingDialog(agenda, students, today, "08:00", 1, window)
        dialog.student.setCurrentIndex(dialog.student.findData(ids[11]))
        dialog.repeat.setChecked(True)
        dialog.show()
        settle(250)
        x, y = place(dialog, 110)
        shots["booking"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["booking_repeat"] = rect_in(dialog.repeat.parentWidget(), dialog, (x, y))
        rects["booking_repeat"] = rects["booking_repeat"].united(rect_in(dialog.student, dialog, (x, y)))
        dialog.close()
        result = agenda.book(ids[11], today, "08:00", 1, repeat_weeks=11)
        window.agenda.refresh()
        toast(window, f"{len(result.created)} horário(s) agendado(s)")
        settle(700)
        shots["booked"] = grab()
        settle(3600)
        clear_toasts()
        try:
            agenda.book(ids[8], today, "07:00")
        except ValueError as error:
            toast(window, str(error), "error")
        settle(700)
        shots["limit"] = grab()
        toast_widget = window.toast_host.findChildren(Toast)[-1]
        rects["toast"] = rect_in(toast_widget, window)
        settle(3600)
        clear_toasts()
        booked = next(card for card in window.agenda.findChildren(SlotCard) if card.item and card.time == "09:00")
        cell = rect_in(booked, window)
        menu = menu_image(window, [("concluido", "Marcar como concluído", "check"), ("falta", "Marcar falta", "x"),
                                   ("profile", "Abrir ficha do aluno", "user"), None,
                                   ("remove", "Desmarcar este dia", "trash"), ("remove_series", "Desmarcar este e os próximos", "repeat")])
        settle(150)
        mx, my = cell.center().x() - 40, cell.bottom() - 6
        shots["agenda_menu"] = compose(grab(), menu.grab().toImage(), mx, my, rounded=False)
        rects["agenda_menu_box"] = QRectF(mx, my, menu.width(), menu.height()).united(cell)
        menu.close()
        rows = agenda.day(today)
        for row in rows[:2]:
            for _trainer, item in row.cells:
                if item:
                    agenda.set_status(item.id, "concluido")
        diego = next(item for _t, item in rows[1].cells if item and item.student_name.startswith("Diego"))
        agenda.set_status(diego.id, "falta")
        window.agenda.refresh()
        settle(300)
        shots["agenda_status"] = grab()
        first = [card for card in window.agenda.findChildren(SlotCard) if card.time in ("06:00", "07:00")]
        area = rect_in(first[0], window)
        for card_widget in first[1:]:
            area = area.united(rect_in(card_widget, window))
        rects["status_rows"] = area

        # Financeiro
        go(4, 900)
        shots["finance_empty"] = grab()
        rects["generate"] = rect_in(button(window.finance, "Gerar mensalidades"), window)
        window.finance.generate()
        settle(700)
        shots["finance"] = grab()
        rects["finance_table"] = rect_in(window.finance.table, window)
        rects["filter"] = rect_in(window.finance.filter, window)
        settle(3600)
        clear_toasts()
        table = window.finance.table
        row_rect = table.visualRect(table.model().index(1, 0))
        row_top = table.viewport().mapTo(window, QPoint(0, row_rect.top())).y()
        row_box = QRectF(rect_in(table, window).left(), row_top, table.width(), row_rect.height())
        menu = menu_image(window, [("pay", "Registrar pagamento", "check"), ("profile", "Abrir ficha do aluno", "user"),
                                   None, ("delete", "Excluir mensalidade", "trash")])
        settle(150)
        mx, my = row_box.left() + 340, row_box.bottom() - 4
        shots["finance_menu"] = compose(grab(), menu.grab().toImage(), mx, my, rounded=False)
        rects["finance_menu_box"] = QRectF(mx, my, menu.width(), menu.height()).united(row_box)
        menu.close()
        record = window.finance.records[table.key(1)]
        dialog = PaymentDialog(finance, record, window)
        dialog.show()
        settle(200)
        x, y = place(dialog, 200)
        shots["payment"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["payment_form"] = rect_in(dialog.amount.parentWidget(), dialog, (x, y))
        dialog.close()
        finance.register(record.id, today, "Pix")
        window.finance.refresh()
        toast(window, f"Pagamento de {record.student_name} registrado")
        settle(700)
        shots["paid"] = grab()
        paid_row = next(r for r in range(table.rowCount()) if table.key(r) == record.id)
        rect = table.visualRect(table.model().index(paid_row, 0))
        top = table.viewport().mapTo(window, QPoint(0, rect.top())).y()
        rects["paid_row"] = QRectF(rect_in(table, window).left(), top, table.width(), rect.height())
        settle(3600)
        clear_toasts()

        # Caixa
        go(5)
        shots["cash"] = grab()
        rects["nav_cash"] = nav(5)
        rects["period"] = rect_in(window.cash.period, window)
        dialog = CashDialog(cash, "saida", today, window)
        dialog.description.setText("Conta de energia")
        dialog.category.setCurrentText("Energia")
        dialog.amount.set_cents(38750)
        dialog.show()
        settle(200)
        x, y = place(dialog, 120)
        shots["cash_dialog"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["cash_form"] = rect_in(dialog.description.parentWidget(), dialog, (x, y))
        dialog.close()

        # Contratos
        go(6)
        shots["contracts"] = grab()
        rects["attach"] = rect_in(button(window.contracts, "Anexar contrato"), window)
        dialog = ContractDialog(window.contract_service, students, ids[3], window)
        dialog.file_label.setText("Contrato_Diego_Ramos.pdf")
        dialog.show()
        settle(200)
        x, y = place(dialog, 120)
        shots["contract_dialog"] = compose(grab(), dialog.grab().toImage(), x, y, 0.55)
        rects["contract_form"] = rect_in(dialog.student.parentWidget(), dialog, (x, y))
        dialog.close()
        table = window.contracts.table
        rect = table.visualRect(table.model().index(0, 0))
        top = table.viewport().mapTo(window, QPoint(0, rect.top())).y()
        row_box = QRectF(rect_in(table, window).left(), top, table.width(), rect.height())
        menu = menu_image(window, [("open", "Abrir contrato", "external"), ("profile", "Abrir ficha do aluno", "user"),
                                   None, ("delete", "Excluir contrato", "trash")])
        settle(150)
        mx, my = row_box.left() + 300, row_box.bottom() - 4
        shots["contract_menu"] = compose(grab(), menu.grab().toImage(), mx, my, rounded=False)
        rects["contract_menu_box"] = QRectF(mx, my, menu.width(), menu.height()).united(row_box)
        menu.close()

        # Relatórios
        go(7, 1300)
        shots["reports"] = grab()
        first_card = window.reports.income
        rects["report_cards"] = rect_in(first_card, window).united(rect_in(window.reports.attendance, window))
        window.reports.chart.hovered = 4
        window.reports.chart.update()
        settle(150)
        shots["reports_hover"] = grab()
        rects["chart"] = rect_in(window.reports.chart, window).adjusted(-20, -50, 20, 10)

        # Backup
        go(8)
        shots["backup"] = grab()
        rects["nav_backup"] = nav(8)
        rects["export"] = rect_in(button(window.backup, "Exportar agora"), window)
        rects["restore"] = rect_in(button(window.backup, "Escolher arquivo"), window).adjusted(-20, -150, 300, 20)
        rects["backup_list"] = rect_in(window.backup.table, window).adjusted(0, -60, 0, 0)

        # Dashboard por último, com todos os dados do dia
        go(0, 900)
        shots["dashboard"] = grab()
        rects["dash_agenda"] = rect_in(window.dashboard.day_agenda.parentWidget(), window)
        rects["nav"] = rect_in(window.navigation.button(0), window).united(rect_in(window.navigation.button(9), window))
        rects["search_hint"] = rect_in(window.search_hint, window)
        rects["toggle"] = rect_in(window.toggle, window)
        entries = [(title, f"Ir para · {detail}", ICONS[i], None) for i, (title, detail) in enumerate(MODULES)]
        entries += [(s.full_name, "Abrir ficha", "user", None) for s in students.list()]
        palette = CommandPalette(entries, window)
        palette.show()
        palette.search.setText("ana")
        settle(300)
        x, y = (CARD_W - palette.width()) / 2, 96
        shots["palette"] = compose(grab(), palette.grab().toImage(), x, y, 0.45)
        rects["palette_box"] = QRectF(x, y, palette.width(), palette.height())
        palette.close()
        window.close()
        engine.dispose()
    return shots, rects


# ----------------------------------------------------------------------------
# Narração
def synthesize(voice: str) -> dict[int, tuple[np.ndarray, float]]:
    folder = STAGING / f"voz-{voice}"
    lines = [{"id": f"{index:03d}", "text": item["text"]} for index, item in enumerate(SCRIPT) if item.get("text")]
    (STAGING / "falas.json").write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PROJECT / "tools/tts_onecore.ps1"),
                    "-Lines", str(STAGING / "falas.json"), "-OutDir", str(folder), "-Voice", voice, "-Rate", "1.02"],
                   check=True, capture_output=True)
    voices = {}
    for line in lines:
        with wave.open(str(folder / f"{line['id']}.wav")) as source:
            rate = source.getframerate()
            data = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float64) / 32768
            if source.getnchannels() == 2:
                data = data.reshape(-1, 2).mean(axis=1)
        # remove silêncio do início/fim e reamostra para 44,1 kHz
        loud = np.where(np.abs(data) > 0.01)[0]
        if len(loud):
            data = data[max(0, loud[0] - int(0.03 * rate)): loud[-1] + int(0.08 * rate)]
        target = np.interp(np.arange(0, len(data) / rate, 1 / 44100), np.arange(len(data)) / rate, data)
        target /= max(1e-6, np.abs(target).max())
        voices[int(line["id"])] = (target * 0.9, len(target) / 44100)
    return voices


# ----------------------------------------------------------------------------
# Linha do tempo
def build_timeline(voices):
    timeline = []
    cursor = 0.0
    for index, item in enumerate(SCRIPT):
        speech = voices.get(index, (None, 0.0))[1]
        if item["kind"] == "card":
            duration = max(item["seconds"], speech + 1.4 if speech else 0)
            voice_at = 0.9
        else:
            duration = max(4.2, speech + 1.5)
            voice_at = 0.55
        timeline.append(dict(index=index, start=cursor, duration=duration, voice_at=cursor + voice_at, speech=speech))
        cursor += duration
    return timeline, cursor


def subtitle_chunks(text: str, speech: float) -> list[tuple[float, float, str]]:
    parts, current = [], ""
    for sentence in text.replace("? ", "?|").replace(". ", ".|").replace(": ", ":|").split("|"):
        if current and len(current) + len(sentence) > 120:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    total = sum(len(part) for part in parts)
    chunks, start = [], 0.0
    for part in parts:
        length = speech * len(part) / total
        chunks.append((start, start + length, part))
        start += length
    return chunks


# ----------------------------------------------------------------------------
# Desenho
def draw_cursor(painter: QPainter, point: QPointF, press: float) -> None:
    painter.save()
    painter.translate(point)
    scale = 1.0 - 0.12 * press
    painter.scale(scale, scale)
    arrow = QPolygonF([QPointF(0, 0), QPointF(0, 26), QPointF(6.5, 20), QPointF(11, 30), QPointF(15, 28),
                       QPointF(10.5, 18.5), QPointF(19, 18.5)])
    painter.setPen(QPen(QColor(10, 10, 12), 2.2))
    painter.setBrush(QColor("#F4F2ED"))
    painter.drawPolygon(arrow)
    painter.restore()


def step_frame(painter: QPainter, item: dict, t: float, shots, rects, previous_point) -> None:
    image = shots[item["image"]]
    target = rects.get(item["target"]) if item["target"] else None
    zoom = 1 + (item["zoom"] - 1) * base.ease((t - 0.9) / 1.3) if target is not None else 1.0
    card_center = QPointF(CARD_W / 2, CARD_H / 2)
    focus = card_center
    if target is not None and item["zoom"] > 1:
        focus = card_center + (target.center() - card_center) * (1 - 1 / zoom)
    painter.save()
    painter.setClipRect(QRectF(0, 0, W, BAND_TOP - 8))
    painter.translate(CENTER)
    painter.scale(FIT * zoom, FIT * zoom)
    painter.translate(-focus)
    frame = QRectF(0, 0, CARD_W, CARD_H)
    for spread in range(48, 0, -6):
        shadow = QPainterPath()
        shadow.addRoundedRect(frame.adjusted(-spread, -spread + 18, spread, spread + 18), 18 + spread, 18 + spread)
        painter.fillPath(shadow, QColor(0, 0, 0, 9))
    clip = QPainterPath()
    clip.addRoundedRect(frame, 12, 12)
    painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
    painter.drawImage(frame, image)
    if target is not None and item["spot"]:
        strength = base.ease((t - 0.7) / 0.6)
        hole = QPainterPath()
        hole.addRoundedRect(target.adjusted(-8, -8, 8, 8), 12, 12)
        shade = QPainterPath()
        shade.addRect(frame)
        painter.fillPath(shade.subtracted(hole), QColor(0, 0, 0, int(120 * strength)))
        pulse = 0.65 + 0.35 * math.sin(t * 3.2)
        painter.setPen(QPen(QColor(201, 169, 107, int(255 * strength * pulse)), 2.5 / (FIT * zoom)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(hole)
    transform = painter.transform()
    painter.restore()

    if target is None:
        return None
    end = transform.map(target.center())
    start = previous_point if previous_point is not None else end + QPointF(160, 120)
    travel = base.ease((t - 0.15) / 0.75)
    point = start + (end - start) * travel
    press = 0.0
    if item["click"] and t > 1.0:
        local = t - 1.0
        press = max(0.0, 1 - abs(local - 0.12) / 0.12) if local < 0.24 else 0.0
        if local < 0.7:
            radius = 8 + 46 * base.out_cubic(local / 0.7)
            painter.setPen(QPen(QColor(201, 169, 107, int(220 * (1 - local / 0.7))), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(end, radius, radius)
    if point.y() < BAND_TOP - 10:
        draw_cursor(painter, point, press)
    return end


def chapter_card(painter: QPainter, item: dict, t: float) -> None:
    reveal = base.out_cubic(t / 1.0)
    painter.save()
    painter.setOpacity(reveal)
    is_title = item["title"] in ("Studio FD Performance", "Pronto!")
    if " · " in item["title"]:
        number, name = item["title"].split(" · ", 1)
        base.draw_text(painter, (0, 380, W, 40), f"CAPÍTULO {number}", 20, GOLD.name(), QFont.Weight.DemiBold,
                       Qt.AlignmentFlag.AlignHCenter, spacing=6)
        base.draw_text(painter, (0, 432 - 12 * (1 - reveal), W, 100), name, 72, "#F4F2ED", QFont.Weight.Light, Qt.AlignmentFlag.AlignHCenter)
    else:
        base.draw_text(painter, (0, 410 - 12 * (1 - reveal), W, 100), item["title"], 78 if is_title else 64, "#F4F2ED",
                       QFont.Weight.Light, Qt.AlignmentFlag.AlignHCenter, spacing=2)
    line = 220 * base.out_cubic((t - 0.3) / 1.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(GOLD)
    painter.drawRect(QRectF(W / 2 - line / 2, 548, line, 1.5))
    base.draw_text(painter, (0, 574, W, 44), item["subtitle"], 26, "#A9A6A0", align=Qt.AlignmentFlag.AlignHCenter,
                   opacity=base.ease((t - 0.6) / 0.8))
    painter.restore()


def band(painter: QPainter, item: dict, local: float, entry: dict) -> None:
    if item["kind"] == "step":
        tag = f"{item['chapter']} / {len(CHAPTERS)}  ·  {CHAPTERS[item['chapter'] - 1].upper()}"
        base.draw_text(painter, (60, BAND_TOP + 4, 600, 24), tag, 15, GOLD.name(), QFont.Weight.DemiBold, spacing=2.5)
    text = item.get("text")
    if not text:
        return
    voice_local = local - (entry["voice_at"] - entry["start"])
    chunks = subtitle_chunks(text, entry["speech"])
    current = None
    for start, end, part in chunks:
        if start - 0.05 <= voice_local < end + 0.6:
            current = (start, part)
    if current is None and voice_local >= 0 and chunks:
        current = (chunks[-1][0], chunks[-1][2])
    if current is None:
        return
    appear = base.ease((voice_local - current[0] + 0.05) / 0.2)
    painter.save()
    painter.setOpacity(appear)
    painter.setFont(base.font(31))
    box = QRectF(160, BAND_TOP + 30, W - 320, H - BAND_TOP - 40)
    painter.setPen(QColor("#F4F2ED"))
    painter.drawText(box, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, current[1])
    painter.restore()


SCRIM = None


def frame_at(absolute: float, timeline, shots, rects, cursor_points) -> QImage:
    image = QImage(W, H, QImage.Format.Format_RGB888)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    base.background(painter, absolute)
    index = next(i for i, entry in enumerate(timeline) if absolute < entry["start"] + entry["duration"] or i == len(timeline) - 1)
    entry = timeline[index]
    local = absolute - entry["start"]
    item = SCRIPT[index]
    fade_in = base.ease(local / STEP_FADE)
    fade_out = 1 - base.ease((local - (entry["duration"] - STEP_FADE)) / STEP_FADE)
    same_next = (index + 1 < len(SCRIPT) and SCRIPT[index + 1]["kind"] == "step" and item["kind"] == "step"
                 and SCRIPT[index + 1]["image"] == item["image"] and item["zoom"] == 1 and SCRIPT[index + 1]["zoom"] == 1)
    same_prev = (index > 0 and SCRIPT[index - 1]["kind"] == "step" and item["kind"] == "step"
                 and SCRIPT[index - 1]["image"] == item["image"] and item["zoom"] == 1 and SCRIPT[index - 1]["zoom"] == 1)
    layer_opacity = (1 if same_prev else fade_in) * (1 if same_next else fade_out)
    if index == 0:
        layer_opacity = base.ease(local / 0.8) * fade_out
    painter.setOpacity(layer_opacity)
    if item["kind"] == "card":
        chapter_card(painter, item, local)
    else:
        previous = cursor_points.get(index - 1)
        cursor_points[index] = step_frame(painter, item, local, shots, rects, previous) or previous
    painter.setOpacity(min(fade_in, fade_out) if not (same_prev or same_next) else 1.0)
    band(painter, item, local, entry)
    painter.end()
    return image


# ----------------------------------------------------------------------------
# Áudio: narração + trilha baixa que abaixa sozinha quando há fala
def mix_audio(path: Path, timeline, total: float, voices) -> None:
    rate = 44100
    size = int((total + 0.5) * rate)
    t = np.arange(size) / rate
    voice = np.zeros(size)
    for entry in timeline:
        data = voices.get(entry["index"], (None, 0))[0]
        if data is None:
            continue
        a = int(entry["voice_at"] * rate)
        b = min(size, a + len(data))
        voice[a:b] += data[: b - a]
    note = lambda midi: 440 * 2 ** ((midi - 69) / 12)
    chords = [[50, 57, 62, 66, 69], [47, 54, 62, 66], [43, 55, 59, 62, 66], [45, 52, 57, 61, 64]]
    bar = 60 / 72 * 4
    music_l, music_r = np.zeros(size), np.zeros(size)
    for number in range(int(total / bar) + 2):
        chord = chords[number % 4]
        start = number * bar
        a, b = int(start * rate), min(size, int((start + bar + 2) * rate))
        if a >= size:
            break
        local = t[a:b] - start
        env = np.minimum(1, local / 1.5) * np.clip((bar + 2 - local) / 2, 0, 1)
        for midi in chord:
            for detune, pan in ((0.998, 0.7), (1.002, 0.3)):
                tone = np.sin(2 * np.pi * note(midi) * detune * t[a:b])
                music_l[a:b] += tone * env * 0.02 * pan
                music_r[a:b] += tone * env * 0.02 * (1 - pan)
    for delay, gain in ((0.037, 0.3), (0.071, 0.24), (0.113, 0.18), (0.167, 0.12)):
        shift = int(delay * rate)
        music_l[shift:] += music_l[:-shift] * gain
        music_r[shift:] += music_r[:-shift] * gain
    music_peak = max(np.abs(music_l).max(), np.abs(music_r).max(), 1e-6)
    music_l, music_r = music_l / music_peak, music_r / music_peak
    envelope = np.abs(voice)
    kernel = np.ones(int(0.25 * rate)) / int(0.25 * rate)
    activity = np.clip(np.convolve(envelope, kernel, mode="same") * 12, 0, 1)
    duck = 0.16 - 0.10 * activity
    fade = np.minimum(1, t / 2) * np.clip((total - t) / 2.5, 0, 1)
    left = (voice * 0.95 + music_l * duck) * fade
    right = (voice * 0.95 + music_r * duck) * fade
    stereo = np.stack([left, right], axis=1)
    stereo /= max(1e-6, np.abs(stereo).max()) / 0.9
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((stereo * 32767).astype("<i2").tobytes())


# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voz", default="Daniel", choices=["Daniel", "Maria"])
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    app = QApplication([])
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "segoeuil.ttf", "segoeuisl.ttf", "georgia.ttf"):
        QFontDatabase.addApplicationFont(str(Path(base.os.environ["WINDIR"]) / "Fonts" / name))
    from studio_fd.views.theme import STYLESHEET, apply_palette
    from studio_fd.widgets.motion import install_wheel_guard
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    apply_palette(app)
    app.setStyleSheet(STYLESHEET)
    install_wheel_guard(app)
    STAGING.mkdir(parents=True, exist_ok=True)
    print("Gerando narração...", flush=True)
    voices = synthesize(args.voz)
    timeline, total = build_timeline(voices)
    print(f"Duração prevista: {total / 60:.1f} min", flush=True)
    print("Capturando telas...", flush=True)
    shots, rects = capture(app)
    missing = {item["target"] for item in SCRIPT if item["kind"] == "step" and item["target"] and item["target"] not in rects}
    missing |= {item["image"] for item in SCRIPT if item["kind"] == "step" and item["image"] not in shots}
    if missing:
        raise SystemExit(f"Faltam capturas: {sorted(missing)}")
    cursor_points = {}
    if args.preview:
        for index, entry in enumerate(timeline):
            if index % 3 == 0 or SCRIPT[index]["kind"] == "card":
                for moment in (entry["start"] + entry["duration"] * 0.6,):
                    for warm in np.arange(entry["start"], moment, 1 / FPS * 6):
                        frame_at(float(warm), timeline, shots, rects, cursor_points)
                    frame_at(moment, timeline, shots, rects, cursor_points).save(str(STAGING / f"preview-{index:02d}.png"))
        print(STAGING, flush=True)
        return

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio = STAGING / f"audio-{args.voz}.wav"
    print("Mixando áudio...", flush=True)
    mix_audio(audio, timeline, total, voices)
    destination = PROJECT / "apresentacao"
    destination.mkdir(exist_ok=True)
    output = destination / "Studio-FD-Performance-Tutorial.mp4"
    temporary = STAGING / "tutorial-render.mp4"
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0", "-i", str(audio),
               "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-tune", "stillimage",
               "-maxrate", "2200k", "-bufsize", "4400k", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(temporary)]
    frames = int(total * FPS)
    with (STAGING / "render.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log, stdout=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            for number in range(frames):
                frame = frame_at(number / FPS, timeline, shots, rects, cursor_points)
                process.stdin.write(bytes(frame.constBits()))
                if number % (FPS * 20) == 0:
                    print(f"{number / FPS / 60:4.1f} / {total / 60:.1f} min", flush=True)
            process.stdin.close()
            if process.wait(timeout=600) != 0:
                raise RuntimeError("O codificador falhou; veja build/tutorial/render.log")
        finally:
            if process.poll() is None:
                process.kill()
    temporary.replace(output)
    print(json.dumps({"file": str(output), "minutes": round(total / 60, 2), "bytes": output.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
