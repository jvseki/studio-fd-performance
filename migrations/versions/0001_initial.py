"""Primeiro schema: planos e alunos. Esta revisão não deve ser editada após uso.

Ajuste posterior só para PostgreSQL (versão web): no SQLite o resultado é idêntico.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Pesquisa sem acentos no PostgreSQL, equivalente à search_key do Python (SQLite).
SEARCH_KEY_POSTGRES = """
CREATE OR REPLACE FUNCTION search_key(texto text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT lower(translate(coalesce(texto, ''),
    'ÁÀÂÃÄÅáàâãäåÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇçÑñÝýÿ',
    'AAAAAAaaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCcNnYyy'))
$$
"""


def _so_sqlite(*constraints):
    """Checagens 0/1 de campos booleanos só existem no SQLite; no PostgreSQL o tipo boolean já garante."""
    return list(constraints) if op.get_context().dialect.name == "sqlite" else []


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
        *_so_sqlite(sa.CheckConstraint("active IN (0, 1)", name="active_boolean")),
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
        *_so_sqlite(sa.CheckConstraint("active IN (0, 1)", name="active_boolean")),
    )
    op.create_index("ix_students_full_name", "students", ["full_name"])
    if op.get_context().dialect.name == "postgresql":
        op.execute(SEARCH_KEY_POSTGRES)


def downgrade() -> None:
    raise RuntimeError("Downgrade destrutivo não é suportado. Restaure um backup compatível.")
