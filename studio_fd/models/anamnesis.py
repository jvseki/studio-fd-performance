from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_fd.database.base import Base
from studio_fd.models.student import Student


class Anamnesis(Base):
    """PDF de anamnese já preenchida, anexado à ficha do aluno.

    O arquivo é copiado para data/anamneses/<aluno>/ com nome interno único;
    aqui ficam o caminho relativo, o nome original e o SHA-256 da cópia.
    Não é contrato: cada aluno pode ter várias anamneses (histórico).
    """

    __tablename__ = "anamneses"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(255), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    attached_on: Mapped[date] = mapped_column(Date)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    student: Mapped[Student] = relationship()
