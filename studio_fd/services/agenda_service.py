"""Agenda diária: cada horário tem uma vaga por personal ativo.

Regras:
- um horário aceita no máximo um aluno por personal ativo (2 personais = 2 alunos);
- o mesmo aluno não ocupa duas vagas no mesmo horário;
- o banco reforça a regra com a restrição única (dia, horário, personal).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from studio_fd.models import Appointment, Student, Trainer
from studio_fd.services.records import AppointmentRecord, TrainerRecord
from studio_fd.services.settings_service import SettingsService, trainer_record
from studio_fd.utils.dates import WEEKDAYS, format_time, parse_time

STATUS_LABELS = {"agendado": "Agendado", "concluido": "Concluído", "falta": "Falta", "cancelado": "Cancelado"}


def appointment_record(item: Appointment) -> AppointmentRecord:
    return AppointmentRecord(item.id, item.day, item.start_time, item.trainer_id, item.trainer.name,
                             item.student_id, item.student.full_name, item.status, item.notes)


@dataclass(frozen=True)
class SlotRow:
    time: str
    cells: list[tuple[TrainerRecord, AppointmentRecord | None]]
    extra: list[AppointmentRecord] = field(default_factory=list)  # personal inativo, mantido visível

    @property
    def booked(self) -> int:
        return sum(1 for _trainer, item in self.cells if item is not None)


@dataclass(frozen=True)
class BookingResult:
    created: list[date]
    skipped: list[tuple[date, str]]


class AgendaService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions
        self.settings = SettingsService(sessions)

    def _load(self, session: Session, start: date, end: date) -> list[Appointment]:
        statement = (select(Appointment).options(joinedload(Appointment.student), joinedload(Appointment.trainer))
                     .where(Appointment.day >= start, Appointment.day <= end, Appointment.status != "cancelado")
                     .order_by(Appointment.day, Appointment.start_time))
        return list(session.scalars(statement))

    def day(self, day: date) -> list[SlotRow]:
        trainers = self.settings.trainers(active_only=True)
        times = self.settings.hours().slots()
        with self.sessions() as session:
            items = [appointment_record(item) for item in self._load(session, day, day)]
        # Atendimentos fora do horário configurado continuam visíveis.
        times = sorted(set(times) | {item.start_time for item in items}, key=parse_time)
        rows = []
        for time in times:
            here = [item for item in items if item.start_time == time]
            by_trainer = {item.trainer_id: item for item in here}
            active_ids = {trainer.id for trainer in trainers}
            rows.append(SlotRow(time, [(trainer, by_trainer.get(trainer.id)) for trainer in trainers],
                                [item for item in here if item.trainer_id not in active_ids]))
        return rows

    def occupancy(self, start: date, days: int = 7) -> dict[date, tuple[int, int]]:
        """Para a faixa de dias da semana: (vagas ocupadas, vagas totais)."""
        capacity = len(self.settings.trainers(active_only=True)) * len(self.settings.hours().slots())
        with self.sessions() as session:
            rows = session.execute(
                select(Appointment.day, func.count(Appointment.id))
                .where(Appointment.day >= start, Appointment.day < start + timedelta(days=days), Appointment.status != "cancelado")
                .group_by(Appointment.day)).all()
        counts = {day: count for day, count in rows}
        return {start + timedelta(days=offset): (counts.get(start + timedelta(days=offset), 0), capacity) for offset in range(days)}

    def book(self, student_id: int, day: date, time: str, trainer_id: int | None = None,
             repeat_weeks: int = 0, notes: str | None = None) -> BookingResult:
        time = format_time(parse_time(time))
        if not 0 <= repeat_weeks <= 52:
            raise ValueError("Repita por no máximo 52 semanas.")
        try:
            return self._book(student_id, day, time, trainer_id, repeat_weeks, notes)
        except IntegrityError as error:
            # Outra janela ocupou a vaga entre a conferência e a gravação.
            raise ValueError("Esse horário acabou de ser ocupado. Atualize a agenda e tente novamente.") from error

    def _book(self, student_id: int, day: date, time: str, trainer_id: int | None,
              repeat_weeks: int, notes: str | None) -> BookingResult:
        created, skipped = [], []
        with self.sessions.begin() as session:
            student = session.get(Student, student_id)
            if student is None:
                raise ValueError("Esse aluno não foi encontrado. Atualize a lista.")
            if not student.active:
                raise ValueError("Esse aluno está inativo. Reative a ficha antes de agendar.")
            trainers = list(session.scalars(select(Trainer).where(Trainer.active.is_(True)).order_by(Trainer.position, Trainer.id)))
            if trainer_id is not None and trainer_id not in {trainer.id for trainer in trainers}:
                raise ValueError("Escolha um personal ativo.")
            for week in range(repeat_weeks + 1):
                current = day + timedelta(weeks=week)
                problem = self._place(session, student_id, current, time, trainer_id, trainers, notes)
                if problem is None:
                    created.append(current)
                elif week == 0 and repeat_weeks == 0:
                    raise ValueError(problem)
                else:
                    skipped.append((current, problem))
        if not created:
            raise ValueError(skipped[0][1] if skipped else "Nenhum horário foi agendado.")
        return BookingResult(created, skipped)

    def _place(self, session: Session, student_id: int, day: date, time: str, trainer_id: int | None,
               trainers: list[Trainer], notes: str | None) -> str | None:
        here = list(session.scalars(select(Appointment).where(Appointment.day == day, Appointment.start_time == time)))
        # Cancelados liberam a vaga: são apagados para não travar a restrição única.
        for item in [item for item in here if item.status == "cancelado"]:
            session.delete(item)
            here.remove(item)
        session.flush()
        if any(item.student_id == student_id for item in here):
            return "Esse aluno já está agendado nesse horário."
        taken = {item.trainer_id for item in here}
        free = [trainer for trainer in trainers if trainer.id not in taken]
        if not free:
            return f"Este horário já atingiu o limite de {len(trainers)} aluno{'s' if len(trainers) != 1 else ''}."
        if trainer_id is not None:
            if trainer_id in taken:
                name = next(trainer.name for trainer in trainers if trainer.id == trainer_id)
                return f"{name} já tem aluno nesse horário."
            chosen = trainer_id
        else:
            chosen = free[0].id
        session.add(Appointment(day=day, start_time=time, trainer_id=chosen, student_id=student_id,
                                notes=(notes or "").strip() or None))
        session.flush()
        return None

    def set_status(self, appointment_id: int, status: str) -> None:
        if status not in STATUS_LABELS:
            raise ValueError("Situação desconhecida.")
        with self.sessions.begin() as session:
            item = session.get(Appointment, appointment_id)
            if item is None:
                raise ValueError("Esse atendimento não existe mais. Atualize a agenda.")
            item.status = status

    def remove(self, appointment_id: int) -> None:
        with self.sessions.begin() as session:
            item = session.get(Appointment, appointment_id)
            if item is not None:
                session.delete(item)

    def remove_future_series(self, appointment_id: int) -> int:
        """Remove este e os próximos atendimentos do aluno no mesmo dia da semana e horário."""
        with self.sessions.begin() as session:
            item = session.get(Appointment, appointment_id)
            if item is None:
                return 0
            later = [other for other in session.scalars(select(Appointment).where(
                Appointment.student_id == item.student_id, Appointment.start_time == item.start_time,
                Appointment.day >= item.day, Appointment.status == "agendado"))
                if other.day.weekday() == item.day.weekday()]
            for other in later:
                session.delete(other)
            return len(later)

    def for_student(self, student_id: int, start: date, days: int = 28) -> list[AppointmentRecord]:
        with self.sessions() as session:
            statement = (select(Appointment).options(joinedload(Appointment.student), joinedload(Appointment.trainer))
                         .where(Appointment.student_id == student_id, Appointment.day >= start,
                                Appointment.day < start + timedelta(days=days), Appointment.status != "cancelado")
                         .order_by(Appointment.day, Appointment.start_time))
            return [appointment_record(item) for item in session.scalars(statement)]

    def habitual(self, student_id: int, today: date | None = None) -> list[str]:
        """Horários habituais a partir das próximas 4 semanas: ["Segunda 18:00", ...]."""
        upcoming = self.for_student(student_id, today or date.today(), 28)
        pairs = sorted({(item.day.weekday(), item.start_time) for item in upcoming}, key=lambda pair: (pair[0], parse_time(pair[1])))
        return [f"{WEEKDAYS[weekday]} {time}" for weekday, time in pairs]
