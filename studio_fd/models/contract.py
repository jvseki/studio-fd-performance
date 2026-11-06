from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_fd.database.base import Base
from studio_fd.models.student import Student


class Contract(Base):
    """Informações do contrato. O PDF fica em data/contratos; aqui só o caminho
    relativo, para que o backup e a troca de computador não quebrem o vínculo."""

    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("signature_type IN ('presencial', 'online')", name="signature_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    signature_type: Mapped[str] = mapped_column(String(12))
    signed_on: Mapped[date] = mapped_column(Date)
    file_path: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    student: Mapped[Student] = relationship()
