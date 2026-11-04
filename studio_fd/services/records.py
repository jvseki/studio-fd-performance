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
