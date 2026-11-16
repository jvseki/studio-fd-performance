"""Anamneses em PDF anexadas à ficha do aluno. Somente cria uma tabela nova."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anamneses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=False, unique=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("attached_on", sa.Date(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("size_bytes > 0", name="size_positive"),
        sa.CheckConstraint("length(sha256) = 64", name="sha256_length"),
    )
    op.create_index("ix_anamneses_student_id", "anamneses", ["student_id"])


def downgrade() -> None:
    raise RuntimeError("Downgrade destrutivo não é suportado. Restaure um backup compatível.")
