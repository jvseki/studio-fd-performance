"""Operação do Studio: personais, agenda, mensalidades, caixa, contratos e configurações.

Somente cria tabelas novas e acrescenta uma coluna opcional em alunos.
Nenhum dado existente é alterado. Esta revisão não deve ser editada após uso.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    trainers = op.create_table(
        "trainers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )
    op.bulk_insert(trainers, [
        {"id": 1, "name": "Personal 1", "position": 1, "active": True},
        {"id": 2, "name": "Personal 2", "position": 2, "active": True},
    ])

    settings = op.create_table(
        "settings",
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.bulk_insert(settings, [
        {"key": "open_time", "value": "06:00"},
        {"key": "close_time", "value": "21:00"},
        {"key": "slot_minutes", "value": "60"},
    ])

    # SQLite não cria chave estrangeira nomeada com ALTER TABLE: o modo batch
    # copia a tabela de alunos para uma nova estrutura, preservando os dados.
    with op.batch_alter_table("students", recreate="always") as batch:
        batch.add_column(sa.Column("trainer_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_students_trainer_id_trainers", "trainers", ["trainer_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("trainer_id", sa.Integer(), sa.ForeignKey("trainers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="agendado"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("day", "start_time", "trainer_id", name="uq_appointments_slot"),
        sa.CheckConstraint("status IN ('agendado', 'concluido', 'falta', 'cancelado')", name="status_valid"),
        sa.CheckConstraint("length(start_time) = 5", name="time_format"),
    )
    op.create_index("ix_appointments_day", "appointments", ["day"])
    op.create_index("ix_appointments_student_day", "appointments", ["student_id", "day"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_month", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("method", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("student_id", "reference_month", name="uq_payments_student_month"),
        sa.CheckConstraint("amount_cents >= 0", name="amount_nonnegative"),
        sa.CheckConstraint("paid_on IS NULL OR method IS NOT NULL", name="paid_has_method"),
    )
    op.create_index("ix_payments_student_id", "payments", ["student_id"])
    op.create_index("ix_payments_reference_month", "payments", ["reference_month"])

    op.create_table(
        "cash_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("description", sa.String(150), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=True, unique=True),
        sa.CheckConstraint("kind IN ('entrada', 'saida')", name="kind_valid"),
        sa.CheckConstraint("amount_cents > 0", name="amount_positive"),
        sa.CheckConstraint("length(trim(description)) > 0", name="description_not_empty"),
    )
    op.create_index("ix_cash_entries_day", "cash_entries", ["day"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signature_type", sa.String(12), nullable=False),
        sa.Column("signed_on", sa.Date(), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("signature_type IN ('presencial', 'online')", name="signature_valid"),
    )
    op.create_index("ix_contracts_student_id", "contracts", ["student_id"])


def downgrade() -> None:
    raise RuntimeError("Downgrade destrutivo não é suportado. Restaure um backup compatível.")
