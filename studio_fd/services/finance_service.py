"""Mensalidades: geração por competência, registro e estorno de pagamento.

Registrar um pagamento cria a entrada correspondente no caixa; desfazer o
pagamento remove essa entrada. Assim Financeiro e Caixa nunca divergem.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from studio_fd.models import CashEntry, Payment, Student
from studio_fd.models.payment import METHODS
from studio_fd.services.records import PaymentRecord
from studio_fd.utils.dates import add_months, day_in_month, first_of_month, month_label

DEFAULT_DUE_DAY = 10


def payment_status(payment: Payment, today: date) -> str:
    if payment.paid_on is not None:
        return "Pago"
    return "Atrasado" if payment.due_date < today else "Pendente"


def payment_record(payment: Payment, today: date) -> PaymentRecord:
    return PaymentRecord(payment.id, payment.student_id, payment.student.full_name, payment.reference_month,
                         payment.amount_cents, payment.due_date, payment.paid_on, payment.method, payment.notes,
                         payment_status(payment, today))


@dataclass(frozen=True)
class MonthSummary:
    expected_cents: int = 0
    received_cents: int = 0
    pending_cents: int = 0
    overdue_cents: int = 0
    paid: int = 0
    pending: int = 0
    overdue: int = 0
    missing: int = 0  # alunos ativos com mensalidade e ainda sem cobrança no mês


class FinanceService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def _query(self):
        return select(Payment).options(joinedload(Payment.student))

    def month(self, month: date, today: date | None = None) -> list[PaymentRecord]:
        today = today or date.today()
        with self.sessions() as session:
            items = session.scalars(self._query().where(Payment.reference_month == first_of_month(month)))
            records = [payment_record(item, today) for item in items]
        order = {"Atrasado": 0, "Pendente": 1, "Pago": 2}
        return sorted(records, key=lambda item: (order[item.status], item.due_date, item.student_name.casefold()))

    def overdue(self, today: date | None = None) -> list[PaymentRecord]:
        today = today or date.today()
        with self.sessions() as session:
            items = session.scalars(self._query().where(Payment.paid_on.is_(None), Payment.due_date < today)
                                    .order_by(Payment.due_date))
            return [payment_record(item, today) for item in items]

    def summary(self, month: date, today: date | None = None) -> MonthSummary:
        records = self.month(month, today)
        missing = len(self._billable(first_of_month(month), {item.student_id for item in records}))
        pick = lambda status: [item for item in records if item.status == status]
        return MonthSummary(
            expected_cents=sum(item.amount_cents for item in records),
            received_cents=sum(item.amount_cents for item in pick("Pago")),
            pending_cents=sum(item.amount_cents for item in pick("Pendente")),
            overdue_cents=sum(item.amount_cents for item in pick("Atrasado")),
            paid=len(pick("Pago")), pending=len(pick("Pendente")), overdue=len(pick("Atrasado")), missing=missing,
        )

    def _billable(self, month: date, already: set[int]) -> list[tuple[int, int, int]]:
        """(aluno, valor, dia de vencimento) de quem ainda não tem cobrança na competência."""
        end = add_months(month, 1)
        with self.sessions() as session:
            students = session.scalars(select(Student).where(Student.active.is_(True), Student.monthly_fee_cents.is_not(None)))
            return [(student.id, student.monthly_fee_cents, student.due_day or DEFAULT_DUE_DAY)
                    for student in students
                    if student.id not in already and (student.starts_on is None or student.starts_on < end)]

    def generate(self, month: date) -> int:
        """Cria as mensalidades da competência para alunos ativos com valor combinado."""
        month = first_of_month(month)
        with self.sessions.begin() as session:
            existing = set(session.scalars(select(Payment.student_id).where(Payment.reference_month == month)))
        pending = self._billable(month, existing)
        with self.sessions.begin() as session:
            for student_id, amount, due_day in pending:
                session.add(Payment(student_id=student_id, reference_month=month, amount_cents=amount,
                                    due_date=day_in_month(month, due_day)))
        return len(pending)

    def add(self, student_id: int, month: date, amount_cents: int, due_date: date, notes: str | None = None) -> None:
        if not isinstance(amount_cents, int) or not 0 < amount_cents <= 999_999_999:
            raise ValueError("Informe um valor maior que zero.")
        month = first_of_month(month)
        with self.sessions.begin() as session:
            if session.get(Student, student_id) is None:
                raise ValueError("Esse aluno não foi encontrado.")
            duplicate = session.scalar(select(Payment.id).where(Payment.student_id == student_id, Payment.reference_month == month))
            if duplicate:
                raise ValueError(f"Esse aluno já tem mensalidade em {month_label(month)}.")
            session.add(Payment(student_id=student_id, reference_month=month, amount_cents=amount_cents,
                                due_date=due_date, notes=(notes or "").strip() or None))

    def register(self, payment_id: int, paid_on: date, method: str, amount_cents: int | None = None) -> None:
        if method not in METHODS:
            raise ValueError("Escolha a forma de pagamento.")
        if paid_on > date.today():
            raise ValueError("A data do pagamento não pode estar no futuro.")
        with self.sessions.begin() as session:
            payment = session.scalar(self._query().where(Payment.id == payment_id))
            if payment is None:
                raise ValueError("Essa mensalidade não existe mais. Atualize a lista.")
            if payment.paid_on is not None:
                raise ValueError("Essa mensalidade já está paga.")
            if amount_cents is not None:
                if not 0 < amount_cents <= 999_999_999:
                    raise ValueError("Informe o valor recebido.")
                payment.amount_cents = amount_cents
            payment.paid_on = paid_on
            payment.method = method
            session.add(CashEntry(day=paid_on, kind="entrada", category="Mensalidade", amount_cents=payment.amount_cents,
                                  method=method, payment_id=payment.id,
                                  description=f"Mensalidade {month_label(payment.reference_month)} · {payment.student.full_name}"[:150]))

    def undo(self, payment_id: int) -> None:
        with self.sessions.begin() as session:
            payment = session.get(Payment, payment_id)
            if payment is None:
                raise ValueError("Essa mensalidade não existe mais. Atualize a lista.")
            entry = session.scalar(select(CashEntry).where(CashEntry.payment_id == payment_id))
            if entry is not None:
                session.delete(entry)
            payment.paid_on = None
            payment.method = None

    def delete(self, payment_id: int) -> None:
        with self.sessions.begin() as session:
            payment = session.get(Payment, payment_id)
            if payment is None:
                return
            if payment.paid_on is not None:
                raise ValueError("Desfaça o pagamento antes de excluir a mensalidade.")
            session.delete(payment)

    def for_student(self, student_id: int, today: date | None = None) -> list[PaymentRecord]:
        today = today or date.today()
        with self.sessions() as session:
            items = session.scalars(self._query().where(Payment.student_id == student_id)
                                    .order_by(Payment.reference_month.desc()))
            return [payment_record(item, today) for item in items]
