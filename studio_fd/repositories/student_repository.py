from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from studio_fd.models import Student
from studio_fd.utils.formatting import search_key


class StudentRepository:
    def __init__(self, session: Session):
        self.session = session

    def count_active(self) -> int:
        statement = select(func.count(Student.id)).where(Student.active.is_(True))
        return self.session.scalar(statement) or 0

    def list(self, query: str = "", letter: str = "", active: bool | None = None) -> list[Student]:
        name_key = func.search_key(Student.full_name)
        statement = select(Student).options(joinedload(Student.plan))
        if query.strip():
            statement = statement.where(name_key.contains(search_key(query.strip()), autoescape=True))
        if letter:
            statement = statement.where(name_key.startswith(search_key(letter), autoescape=True))
        if active is not None:
            statement = statement.where(Student.active.is_(active))
        return list(self.session.scalars(statement.order_by(name_key, Student.id)))

    def get(self, student_id: int) -> Student | None:
        statement = select(Student).options(joinedload(Student.plan)).where(Student.id == student_id)
        return self.session.scalar(statement)

    def with_cpf(self, cpf: str) -> Student | None:
        return self.session.scalar(select(Student).where(Student.cpf == cpf))
