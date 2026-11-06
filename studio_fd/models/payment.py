from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_fd.database.base import Base
from studio_fd.models.student import Student

METHODS = ("Pix", "Dinheiro", "Débito", "Crédito", "Outro")


class Payment(Base):
    """Mensalidade de um aluno em uma competência (mês de referência).

    O status não é guardado: "Pago" quando há data de pagamento, "Atrasado"
    quando o vencimento passou, senão "Pendente". Assim ele nunca fica velho.
    """

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("student_id", "reference_month", name="uq_payments_student_month"),
        CheckConstraint("amount_cents >= 0", name="amount_nonnegative"),
        CheckConstraint("paid_on IS NULL OR method IS NOT NULL", name="paid_has_method"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    reference_month: Mapped[date] = mapped_column(Date, index=True)  # sempre dia 1
    amount_cents: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    paid_on: Mapped[date | None] = mapped_column(Date)
    method: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    student: Mapped[Student] = relationship()
