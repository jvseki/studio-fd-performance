"""Primeiro schema: planos e alunos. Esta revisão não deve ser editada após uso."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("workouts_per_week", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        sa.CheckConstraint("workouts_per_week BETWEEN 1 AND 7", name="workouts_range"),
        sa.CheckConstraint("price_cents >= 0", name="price_nonnegative"),
        sa.CheckConstraint("duration_months > 0", name="duration_positive"),
        sa.CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("cpf", sa.String(11), nullable=True, unique=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("registered_on", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT")),
        sa.Column("monthly_fee_cents", sa.Integer(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="name_not_empty"),
        sa.CheckConstraint("monthly_fee_cents IS NULL OR monthly_fee_cents >= 0", name="fee_nonnegative"),
        sa.CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="due_day_range"),
        sa.CheckConstraint("active IN (0, 1)", name="active_boolean"),
    )
    op.create_index("ix_students_full_name", "students", ["full_name"])


def downgrade() -> None:
    raise RuntimeError("Downgrade destrutivo não é suportado. Restaure um backup compatível.")
