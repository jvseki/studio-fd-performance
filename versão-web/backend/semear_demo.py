r"""Cria dados FICTÍCIOS para demonstração em uma pasta separada.
Uso: ..\..\.venv\Scripts\python.exe semear_demo.py dados-demo
"""

from datetime import date, timedelta
from pathlib import Path
import shutil
import sys

from app import Services
from studio_fd.services.records import CashInput, PlanInput, StudentInput
from studio_fd.utils.paths import AppPaths

pasta = Path(sys.argv[1] if len(sys.argv) > 1 else "dados-demo")
if pasta.exists():
    shutil.rmtree(pasta)
s = Services(AppPaths(pasta))
s.settings.save_trainer("Douglas", True, 1)
s.settings.save_trainer("Fran", True, 2)
planos = {}
for nome, vezes, valor in (("Individual 2x", 2, 35000), ("Individual 3x", 3, 45000), ("Individual 4x", 4, 55000),
                           ("Individual 5x", 5, 65000), ("Casal 2x", 2, 60000), ("Casal 3x", 3, 70000)):
    planos[nome] = s.plans.save(PlanInput(nome, vezes, valor, 1))
alunos = [("Ana Beatriz Souza", "Individual 3x", 5), ("Bruno Carvalho", "Individual 2x", 10), ("Carla Mendes", "Individual 5x", 15),
          ("Diego Ramos", "Individual 3x", 5), ("Eduarda Lima", "Individual 2x", 10), ("Felipe Nogueira", "Individual 4x", 15),
          ("Gabriela Rocha", "Casal 3x", 5), ("Henrique Alves", "Casal 3x", 5), ("Isabela Torres", "Individual 4x", 10),
          ("João Pedro Martins", "Individual 3x", 15), ("Juliana Santos", "Individual 2x", 10), ("Lucas Ferreira", "Individual 5x", 5)]
ids = []
for i, (nome, plano, dia) in enumerate(alunos):
    p = planos[plano]
    valor = p.price_cents // 2 if plano.startswith("Casal") else p.price_cents
    ids.append(s.students.save(StudentInput(nome, f"18997{i:06d}", plan_id=p.id, monthly_fee_cents=valor, due_day=dia,
                                            trainer_id=1 + i % 2, starts_on=date.today() - timedelta(days=200))).id)
segunda = date.today() - timedelta(days=date.today().weekday())
for hora, quem in (("06:00", [0, 1]), ("07:00", [2, 3]), ("08:00", [4]), ("09:00", [6, 7]), ("17:00", [8, 9]), ("18:00", [10, 11]), ("19:00", [5])):
    for dia_semana in range(5):  # segunda a sexta
        for q in quem:
            if (dia_semana + q) % 4 != 3:  # deixa algumas vagas livres
                s.agenda.book(ids[q], segunda + timedelta(days=dia_semana), hora, repeat_weeks=3)
for linha in s.agenda.day(date.today())[:2]:
    for _p, item in linha.cells:
        if item:
            s.agenda.set_status(item.id, "concluido")
mes = date.today().replace(day=1)
anterior = (mes - timedelta(days=1)).replace(day=1)
for m in (anterior, mes):
    s.finance.generate(m)
for i, item in enumerate(s.finance.month(anterior)):
    if i != 3:
        s.finance.register(item.id, item.due_date, ("Pix", "Dinheiro", "Crédito")[i % 3])
for i, item in enumerate(s.finance.month(mes)):
    if item.due_date <= date.today() and i % 3 != 1:
        s.finance.register(item.id, item.due_date, "Pix")
s.cash.add(CashInput(date.today(), "Avaliação física", "Avaliação", "entrada", 12000, "Pix"))
s.cash.add(CashInput(date.today(), "Conta de energia", "Energia", "saida", 38750, "Pix"))
s.cash.add(CashInput(anterior.replace(day=5), "Aluguel do espaço", "Aluguel", "saida", 250000, "Pix"))
pdf = pasta / "anamnese-ficticia.pdf"
pdf.write_bytes(b"%PDF-1.4\n% anamnese ficticia\n%%EOF\n")
s.anamneses.add(ids[0], pdf, date.today() - timedelta(days=30), "Avaliação inicial")
# Acesso de teste, SÓ no modo demonstração (sem Supabase): e-mail e senha aparecem na tela de entrada.
s.acesso.criar("demo@studiofd.com.br", "Demonstração", "studiofd2026", "admin")
s.engine.dispose()
print("dados de demonstração em", pasta.resolve())
