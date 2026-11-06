"""Caixa simples: entradas, saídas e saldo por período."""

from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import CashEntry
from studio_fd.models.payment import METHODS
from studio_fd.services.records import CashInput, CashRecord

INCOME_CATEGORIES = ["Mensalidade", "Avaliação", "Aula avulsa", "Venda", "Outros"]
EXPENSE_CATEGORIES = ["Aluguel", "Energia", "Água", "Internet", "Equipamentos", "Manutenção",
                      "Limpeza", "Pagamento de personal", "Marketing", "Impostos", "Outros"]


def cash_record(entry: CashEntry) -> CashRecord:
    return CashRecord(**{name: getattr(entry, name) for name in CashRecord.__dataclass_fields__})


@dataclass(frozen=True)
class CashTotals:
    income_cents: int
    expense_cents: int

    @property
    def balance_cents(self) -> int:
        return self.income_cents - self.expense_cents


class CashService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def entries(self, start: date, end: date) -> list[CashRecord]:
        with self.sessions() as session:
            statement = (select(CashEntry).where(CashEntry.day >= start, CashEntry.day <= end)
                         .order_by(CashEntry.day.desc(), CashEntry.id.desc()))
            return [cash_record(entry) for entry in session.scalars(statement)]

    def totals(self, start: date, end: date) -> CashTotals:
        records = self.entries(start, end)
        return CashTotals(sum(item.amount_cents for item in records if item.kind == "entrada"),
                          sum(item.amount_cents for item in records if item.kind == "saida"))

    def add(self, data: CashInput) -> CashRecord:
        values = asdict(data)
        values["description"] = " ".join(data.description.split())
        if not values["description"] or len(values["description"]) > 150:
            raise ValueError("Descreva a movimentação em até 150 caracteres.")
        if data.kind not in ("entrada", "saida"):
            raise ValueError("Escolha entrada ou saída.")
        if not isinstance(data.amount_cents, int) or not 0 < data.amount_cents <= 999_999_999:
            raise ValueError("Informe um valor maior que zero.")
        if data.method is not None and data.method not in METHODS:
            raise ValueError("Escolha uma forma de pagamento válida.")
        values["category"] = (data.category or "Outros").strip()[:60] or "Outros"
        values["notes"] = (data.notes or "").strip() or None
        with self.sessions.begin() as session:
            entry = CashEntry(**values)
            session.add(entry)
            session.flush()
            return cash_record(entry)

    def delete(self, entry_id: int) -> None:
        with self.sessions.begin() as session:
            entry = session.get(CashEntry, entry_id)
            if entry is None:
                return
            if entry.payment_id is not None:
                raise ValueError("Essa entrada veio de uma mensalidade. Desfaça o pagamento em Financeiro.")
            session.delete(entry)
