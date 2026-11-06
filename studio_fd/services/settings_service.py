"""Horário de funcionamento e personais do Studio.

Os personais ativos definem as colunas da agenda e, portanto, quantos
alunos cabem em cada horário.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import Appointment, Setting, Trainer
from studio_fd.services.records import TrainerRecord
from studio_fd.utils.dates import format_time, parse_time

DEFAULTS = {"open_time": "06:00", "close_time": "21:00", "slot_minutes": "60"}


@dataclass(frozen=True)
class StudioHours:
    open_time: str
    close_time: str
    slot_minutes: int

    def slots(self) -> list[str]:
        start, end = parse_time(self.open_time), parse_time(self.close_time)
        return [format_time(minute) for minute in range(start, end, self.slot_minutes)]


def trainer_record(trainer: Trainer) -> TrainerRecord:
    return TrainerRecord(trainer.id, trainer.name, trainer.position, trainer.active)


class SettingsService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    # Horário -----------------------------------------------------------
    def hours(self) -> StudioHours:
        with self.sessions() as session:
            stored = {row.key: row.value for row in session.scalars(select(Setting))}
        values = DEFAULTS | stored
        return StudioHours(values["open_time"], values["close_time"], int(values["slot_minutes"]))

    def save_hours(self, open_time: str, close_time: str, slot_minutes: int) -> StudioHours:
        start, end = parse_time(open_time), parse_time(close_time)
        if slot_minutes not in (30, 45, 60, 90):
            raise ValueError("Escolha atendimentos de 30, 45, 60 ou 90 minutos.")
        if end - start < slot_minutes:
            raise ValueError("O horário de fechamento precisa ser depois da abertura.")
        values = {"open_time": format_time(start), "close_time": format_time(end), "slot_minutes": str(slot_minutes)}
        with self.sessions.begin() as session:
            for key, value in values.items():
                session.merge(Setting(key=key, value=value))
        return self.hours()

    # Personais ---------------------------------------------------------
    def trainers(self, active_only: bool = False) -> list[TrainerRecord]:
        with self.sessions() as session:
            statement = select(Trainer).order_by(Trainer.position, Trainer.id)
            if active_only:
                statement = statement.where(Trainer.active.is_(True))
            return [trainer_record(trainer) for trainer in session.scalars(statement)]

    def save_trainer(self, name: str, active: bool = True, trainer_id: int | None = None) -> TrainerRecord:
        name = " ".join(name.split())
        if not name or len(name) > 80:
            raise ValueError("Informe o nome do personal, com até 80 caracteres.")
        with self.sessions.begin() as session:
            if trainer_id is None:
                position = (session.scalar(select(func.max(Trainer.position))) or 0) + 1
                trainer = Trainer(position=position)
            else:
                trainer = session.get(Trainer, trainer_id)
                if trainer is None:
                    raise ValueError("Esse personal não foi encontrado. Atualize a tela.")
            if trainer_id is not None and trainer.active and not active:
                future = session.scalar(select(func.count(Appointment.id)).where(
                    Appointment.trainer_id == trainer_id, Appointment.day >= date.today(),
                    Appointment.status == "agendado"))
                if future:
                    raise ValueError(f"{trainer.name} tem {future} atendimento(s) agendado(s). "
                                     "Remaneje esses horários antes de desativar.")
                remaining = session.scalar(select(func.count(Trainer.id)).where(
                    Trainer.active.is_(True), Trainer.id != trainer_id))
                if not remaining:
                    raise ValueError("Mantenha pelo menos um personal ativo para a agenda funcionar.")
            trainer.name = name
            trainer.active = active
            session.add(trainer)
            session.flush()
            return trainer_record(trainer)
