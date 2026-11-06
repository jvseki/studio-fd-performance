from dataclasses import asdict
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import Student, Trainer
from studio_fd.repositories.plan_repository import PlanRepository
from studio_fd.repositories.student_repository import StudentRepository
from studio_fd.services.records import StudentInput, StudentRecord
from studio_fd.utils.formatting import normalize_cpf, normalize_phone


def student_record(student: Student) -> StudentRecord:
    derived = ("plan_name", "workouts_per_week", "trainer_name")
    fields = {name: getattr(student, name) for name in StudentRecord.__dataclass_fields__ if name not in derived}
    return StudentRecord(**fields, plan_name=student.plan.name if student.plan else None,
                         workouts_per_week=student.plan.workouts_per_week if student.plan else None,
                         trainer_name=student.trainer.name if student.trainer else None)


class StudentService:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

    def list(self, query: str = "", letter: str = "", active: bool | None = None) -> list[StudentRecord]:
        with self.sessions() as session:
            return [student_record(student) for student in StudentRepository(session).list(query, letter, active)]

    def get(self, student_id: int) -> StudentRecord:
        with self.sessions() as session:
            student = StudentRepository(session).get(student_id)
            if student is None:
                raise ValueError("Esse aluno não foi encontrado. Atualize a lista.")
            return student_record(student)

    def save(self, data: StudentInput, student_id: int | None = None) -> StudentRecord:
        values = asdict(data)
        values["full_name"] = " ".join(data.full_name.split())
        if not values["full_name"] or len(values["full_name"]) > 150:
            raise ValueError("Informe o nome do aluno, com até 150 caracteres.")
        values["phone"] = normalize_phone(data.phone)
        values["cpf"] = normalize_cpf(data.cpf)
        if data.birth_date and data.birth_date > date.today():
            raise ValueError("A data de nascimento não pode estar no futuro.")
        if data.monthly_fee_cents is not None and (not isinstance(data.monthly_fee_cents, int) or not 0 <= data.monthly_fee_cents <= 999_999_999):
            raise ValueError("Informe um valor válido para a mensalidade.")
        if data.due_day is not None and not 1 <= data.due_day <= 31:
            raise ValueError("O vencimento precisa ser um dia entre 1 e 31.")
        values["address"] = (data.address or "").strip() or None
        if values["address"] and len(values["address"]) > 255:
            raise ValueError("O endereço precisa ter até 255 caracteres.")
        values["notes"] = (data.notes or "").strip() or None
        try:
            with self.sessions.begin() as session:
                repository = StudentRepository(session)
                student = repository.get(student_id) if student_id is not None else Student()
                if student is None:
                    raise ValueError("Esse aluno não foi encontrado. Atualize a lista.")
                if values["cpf"]:
                    duplicate = repository.with_cpf(values["cpf"])
                    if duplicate is not None and duplicate.id != student_id:
                        raise ValueError("Esse CPF já está cadastrado para outro aluno.")
                if data.plan_id is not None:
                    plan = PlanRepository(session).get(data.plan_id)
                    if plan is None:
                        raise ValueError("O plano escolhido não existe mais. Escolha outro plano.")
                    if not plan.active and student.plan_id != plan.id:
                        raise ValueError("Esse plano está inativo. Escolha um plano ativo.")
                if data.trainer_id is not None and session.get(Trainer, data.trainer_id) is None:
                    raise ValueError("O personal escolhido não existe mais. Escolha outro.")
                for name, value in values.items():
                    setattr(student, name, value)
                session.add(student)
                session.flush()
                # Recarrega as relações quando o plano ou o personal mudam.
                session.expire(student, ["plan", "trainer"])
                return student_record(student)
        except IntegrityError as error:
            raise ValueError("Não foi possível salvar. Confira se o CPF já está cadastrado e atualize a lista de planos.") from error
