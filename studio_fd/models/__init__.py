"""Importar este pacote registra os modelos no metadata do SQLAlchemy."""

from studio_fd.models.plan import Plan
from studio_fd.models.student import Student

__all__ = ["Plan", "Student"]
