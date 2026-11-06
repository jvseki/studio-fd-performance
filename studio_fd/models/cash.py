from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from studio_fd.database.base import Base


class CashEntry(Base):
    """Movimentação do caixa. Recebimentos de mensalidade entram sozinhos,
    ligados ao pagamento: desfazer o pagamento remove a entrada."""

    __tablename__ = "cash_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('entrada', 'saida')", name="kind_valid"),
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint("length(trim(description)) > 0", name="description_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(8))
    amount_cents: Mapped[int] = mapped_column(Integer)
    method: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True)
