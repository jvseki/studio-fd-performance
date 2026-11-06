"""Relatórios da operação a partir do caixa, da agenda e dos cadastros."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import Appointment, CashEntry, Student
from studio_fd.services.dashboard_service import DashboardService
from studio_fd.utils.dates import add_months, first_of_month


@dataclass(frozen=True)
class MonthFlow:
    month: date
    income_cents: int
    expense_cents: int


@dataclass(frozen=True)
class Report:
    month: date
    flows: list[MonthFlow]
    attendance: dict[str, int]
    expenses_by_category: list[tuple[str, int]]
    by_plan: list[tuple[str, int]]
    new_students: int
    active_students: int
    top_students: list[tuple[str, int]] = field(default_factory=list)

    @property
    def current(self) -> MonthFlow:
        return self.flows[-1]


class ReportService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def build(self, month: date, months: int = 6) -> Report:
        month = first_of_month(month)
        start = add_months(month, -(months - 1))
        end = add_months(month, 1)
        with self.sessions() as session:
            entries = session.execute(select(CashEntry.day, CashEntry.kind, CashEntry.amount_cents, CashEntry.category)
                                      .where(CashEntry.day >= start, CashEntry.day < end)).all()
            attendance = dict(session.execute(
                select(Appointment.status, func.count(Appointment.id))
                .where(Appointment.day >= month, Appointment.day < end).group_by(Appointment.status)).all())
            top = session.execute(
                select(Student.full_name, func.count(Appointment.id)).join(Appointment, Appointment.student_id == Student.id)
                .where(Appointment.day >= month, Appointment.day < end, Appointment.status == "concluido")
                .group_by(Student.id).order_by(func.count(Appointment.id).desc(), Student.full_name).limit(5)).all()
            new_students = session.scalar(select(func.count(Student.id)).where(
                Student.registered_on >= month, Student.registered_on < end)) or 0
        flows = []
        for offset in range(months):
            current = add_months(start, offset)
            following = add_months(current, 1)
            rows = [row for row in entries if current <= row.day < following]
            flows.append(MonthFlow(current, sum(row.amount_cents for row in rows if row.kind == "entrada"),
                                   sum(row.amount_cents for row in rows if row.kind == "saida")))
        categories: dict[str, int] = {}
        for row in entries:
            if row.kind == "saida" and row.day >= month:
                categories[row.category] = categories.get(row.category, 0) + row.amount_cents
        summary = DashboardService(self.sessions).summary()
        return Report(month, flows, attendance,
                      sorted(categories.items(), key=lambda item: -item[1]),
                      summary.by_plan, new_students, summary.active_students,
                      [(name, count) for name, count in top])
