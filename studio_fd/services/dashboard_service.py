"""Indicadores do Dashboard calculados a partir dos cadastros existentes.

Nada aqui depende de pagamentos: os valores são as mensalidades combinadas
na ficha de cada aluno ativo, e os vencimentos usam o dia informado.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session, joinedload, sessionmaker
from sqlalchemy import select

from studio_fd.models import Student
from studio_fd.repositories.student_repository import StudentRepository


@dataclass(frozen=True)
class UpcomingDue:
    student_id: int
    name: str
    plan_name: str | None
    fee_cents: int | None
    due_date: date
    days: int


@dataclass(frozen=True)
class DashboardSummary:
    active_students: int
    total_students: int = 0
    monthly_revenue_cents: int = 0
    average_fee_cents: int | None = None
    due_this_week: int = 0
    upcoming: list[UpcomingDue] = field(default_factory=list)
    by_plan: list[tuple[str, int]] = field(default_factory=list)


def next_due(due_day: int, today: date) -> date:
    def in_month(year: int, month: int) -> date:
        return date(year, month, min(due_day, calendar.monthrange(year, month)[1]))

    current = in_month(today.year, today.month)
    if current >= today:
        return current
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return in_month(year, month)


class DashboardService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def summary(self, today: date | None = None) -> DashboardSummary:
        today = today or date.today()
        with self.sessions() as session:
            active_count = StudentRepository(session).count_active()
            students = list(session.scalars(select(Student).options(joinedload(Student.plan))))
            active = [student for student in students if student.active]
            fees = [student.monthly_fee_cents for student in active if student.monthly_fee_cents]
            upcoming = []
            for student in active:
                if student.due_day:
                    due = next_due(student.due_day, today)
                    upcoming.append(UpcomingDue(student.id, student.full_name, student.plan.name if student.plan else None,
                                                student.monthly_fee_cents, due, (due - today).days))
            upcoming.sort(key=lambda item: (item.days, item.name.casefold()))
            counts: dict[str, int] = {}
            for student in active:
                name = student.plan.name if student.plan else "Sem plano"
                counts[name] = counts.get(name, 0) + 1
            return DashboardSummary(
                active_students=active_count,
                total_students=len(students),
                monthly_revenue_cents=sum(fees),
                average_fee_cents=sum(fees) // len(fees) if fees else None,
                due_this_week=sum(1 for item in upcoming if item.days <= 7),
                upcoming=upcoming,
                by_plan=sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold())),
            )
