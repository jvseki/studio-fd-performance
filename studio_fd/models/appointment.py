from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_fd.database.base import Base
from studio_fd.models.student import Student
from studio_fd.models.trainer import Trainer

STATUSES = ("agendado", "concluido", "falta", "cancelado")


class Appointment(Base):
    """Um atendimento em um dia e horário, com um personal.

    A restrição única (dia, horário, personal) é a garantia final do limite:
    mesmo que a interface falhe, o banco não aceita dois alunos na mesma
    coluna do mesmo horário.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("day", "start_time", "trainer_id", name="uq_appointments_slot"),
        CheckConstraint("status IN ('agendado', 'concluido', 'falta', 'cancelado')", name="status_valid"),
        CheckConstraint("length(start_time) = 5", name="time_format"),
        Index("ix_appointments_student_day", "student_id", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[str] = mapped_column(String(5))  # "HH:MM"
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainers.id", ondelete="RESTRICT"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(12), default="agendado", server_default="agendado")
    notes: Mapped[str | None] = mapped_column(Text)
    student: Mapped[Student] = relationship()
    trainer: Mapped[Trainer] = relationship()
