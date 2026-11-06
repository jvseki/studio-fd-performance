"""Importar este pacote registra os modelos no metadata do SQLAlchemy."""

from studio_fd.models.plan import Plan
from studio_fd.models.trainer import Trainer
from studio_fd.models.student import Student
from studio_fd.models.appointment import Appointment
from studio_fd.models.payment import Payment
from studio_fd.models.cash import CashEntry
from studio_fd.models.contract import Contract
from studio_fd.models.setting import Setting

__all__ = ["Appointment", "CashEntry", "Contract", "Payment", "Plan", "Setting", "Student", "Trainer"]
