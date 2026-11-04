from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_fd.models import Plan


class PlanRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self) -> list[Plan]:
        return list(self.session.scalars(select(Plan).order_by(Plan.active.desc(), func.search_key(Plan.name), Plan.id)))

    def get(self, plan_id: int) -> Plan | None:
        return self.session.get(Plan, plan_id)
