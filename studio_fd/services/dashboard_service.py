from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from studio_fd.repositories.student_repository import StudentRepository


@dataclass(frozen=True)
class DashboardSummary:
    active_students: int


class DashboardService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def summary(self) -> DashboardSummary:
        with self.sessions() as session:
            return DashboardSummary(active_students=StudentRepository(session).count_active())
