from dataclasses import asdict

from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import Plan
from studio_fd.repositories.plan_repository import PlanRepository
from studio_fd.services.records import PlanInput, PlanRecord


def plan_record(plan: Plan) -> PlanRecord:
    return PlanRecord(**{name: getattr(plan, name) for name in PlanRecord.__dataclass_fields__})


class PlanService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def list(self) -> list[PlanRecord]:
        with self.sessions() as session:
            return [plan_record(plan) for plan in PlanRepository(session).list()]

    def get(self, plan_id: int) -> PlanRecord:
        with self.sessions() as session:
            plan = PlanRepository(session).get(plan_id)
            if plan is None:
                raise ValueError("Esse plano não foi encontrado. Atualize a lista.")
            return plan_record(plan)

    def save(self, data: PlanInput, plan_id: int | None = None) -> PlanRecord:
        values = asdict(data)
        values["name"] = " ".join(data.name.split())
        if not values["name"] or len(values["name"]) > 100:
            raise ValueError("Informe um nome para o plano, com até 100 caracteres.")
        if not 1 <= data.workouts_per_week <= 7:
            raise ValueError("Escolha entre 1 e 7 treinos por semana.")
        if not isinstance(data.price_cents, int) or not 0 <= data.price_cents <= 999_999_999:
            raise ValueError("Informe um valor válido para o plano.")
        if not 1 <= data.duration_months <= 120:
            raise ValueError("Informe a duração do plano entre 1 e 120 meses.")
        values["description"] = (data.description or "").strip() or None
        with self.sessions.begin() as session:
            plan = PlanRepository(session).get(plan_id) if plan_id is not None else Plan()
            if plan is None:
                raise ValueError("Esse plano não foi encontrado. Atualize a lista.")
            for name, value in values.items():
                setattr(plan, name, value)
            session.add(plan)
            session.flush()
            return plan_record(plan)
