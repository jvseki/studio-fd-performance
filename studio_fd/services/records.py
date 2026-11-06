"""Dados simples que circulam entre os serviços e a interface."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PlanInput:
    name: str
    workouts_per_week: int
    price_cents: int
    duration_months: int
    description: str | None = None
    active: bool = True


@dataclass(frozen=True)
class PlanRecord:
    id: int
    name: str
    workouts_per_week: int
    price_cents: int
    duration_months: int
    description: str | None
    active: bool


@dataclass(frozen=True)
class StudentInput:
    full_name: str
    phone: str
    birth_date: date | None = None
    cpf: str | None = None
    address: str | None = None
    active: bool = True
    notes: str | None = None
    plan_id: int | None = None
    monthly_fee_cents: int | None = None
    starts_on: date | None = None
    due_day: int | None = None
    trainer_id: int | None = None


@dataclass(frozen=True)
class StudentRecord:
    id: int
    full_name: str
    phone: str
    birth_date: date | None
    cpf: str | None
    address: str | None
    registered_on: date
    active: bool
    notes: str | None
    plan_id: int | None
    plan_name: str | None
    workouts_per_week: int | None
    monthly_fee_cents: int | None
    starts_on: date | None
    due_day: int | None
    trainer_id: int | None = None
    trainer_name: str | None = None


@dataclass(frozen=True)
class TrainerRecord:
    id: int
    name: str
    position: int
    active: bool


@dataclass(frozen=True)
class AppointmentRecord:
    id: int
    day: date
    start_time: str
    trainer_id: int
    trainer_name: str
    student_id: int
    student_name: str
    status: str
    notes: str | None


@dataclass(frozen=True)
class PaymentRecord:
    id: int
    student_id: int
    student_name: str
    reference_month: date
    amount_cents: int
    due_date: date
    paid_on: date | None
    method: str | None
    notes: str | None
    status: str  # "Pago", "Pendente" ou "Atrasado"


@dataclass(frozen=True)
class CashInput:
    day: date
    description: str
    category: str
    kind: str  # "entrada" ou "saida"
    amount_cents: int
    method: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CashRecord:
    id: int
    day: date
    description: str
    category: str
    kind: str
    amount_cents: int
    method: str | None
    notes: str | None
    payment_id: int | None


@dataclass(frozen=True)
class ContractRecord:
    id: int
    student_id: int
    student_name: str
    signature_type: str
    signed_on: date
    file_path: str | None
    notes: str | None
