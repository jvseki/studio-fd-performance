"""Contratos: o PDF é copiado para data/contratos/<aluno>/ e o banco guarda
apenas o caminho relativo. Excluir um contrato move o arquivo para
contratos/_removidos em vez de apagá-lo."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from studio_fd.models import Contract, Student
from studio_fd.services.records import ContractRecord
from studio_fd.utils.formatting import search_key
from studio_fd.utils.paths import AppPaths

MAX_PDF_BYTES = 50 * 1024 * 1024
SIGNATURES = {"presencial": "Presencial", "online": "Online"}


def contract_record(item: Contract) -> ContractRecord:
    return ContractRecord(item.id, item.student_id, item.student.full_name, item.signature_type,
                          item.signed_on, item.file_path, item.notes)


class ContractService:
    def __init__(self, sessions: sessionmaker[Session], paths: AppPaths):
        self.sessions = sessions
        self.paths = paths

    def list(self, query: str = "") -> list[ContractRecord]:
        with self.sessions() as session:
            statement = select(Contract).options(joinedload(Contract.student)).order_by(Contract.signed_on.desc(), Contract.id.desc())
            records = [contract_record(item) for item in session.scalars(statement)]
        key = search_key(query.strip())
        return [item for item in records if key in search_key(item.student_name)] if key else records

    def for_student(self, student_id: int) -> list[ContractRecord]:
        return [item for item in self.list() if item.student_id == student_id]

    def file(self, record: ContractRecord) -> Path | None:
        if not record.file_path:
            return None
        root = self.paths.contracts.resolve()
        target = (root / record.file_path).resolve()
        if not target.is_relative_to(root):
            raise ValueError("O caminho do contrato é inválido.")
        return target

    def add(self, student_id: int, signature_type: str, signed_on: date, pdf: Path | None, notes: str | None = None) -> ContractRecord:
        if signature_type not in SIGNATURES:
            raise ValueError("Escolha se o contrato foi assinado presencialmente ou online.")
        if signed_on > date.today():
            raise ValueError("A data da assinatura não pode estar no futuro.")
        relative = None
        if pdf is not None:
            pdf = Path(pdf)
            if not pdf.is_file():
                raise ValueError("O arquivo escolhido não foi encontrado.")
            if pdf.stat().st_size > MAX_PDF_BYTES:
                raise ValueError("O PDF passa de 50 MB. Reduza o arquivo e tente novamente.")
            with pdf.open("rb") as reader:
                if reader.read(5) != b"%PDF-":
                    raise ValueError("O arquivo escolhido não é um PDF válido.")
        with self.sessions.begin() as session:
            student = session.get(Student, student_id)
            if student is None:
                raise ValueError("Esse aluno não foi encontrado.")
            item = Contract(student_id=student_id, signature_type=signature_type, signed_on=signed_on,
                            notes=(notes or "").strip() or None)
            session.add(item)
            session.flush()
            if pdf is not None:
                folder = self.paths.contracts / str(student_id)
                folder.mkdir(parents=True, exist_ok=True)
                name = f"contrato_{item.id}_{signed_on:%Y%m%d}_{uuid4().hex[:6]}.pdf"
                shutil.copy2(pdf, folder / name)
                relative = f"{student_id}/{name}"
                item.file_path = relative
            session.flush()
            session.refresh(item, ["student"])
            return contract_record(item)

    def delete(self, contract_id: int) -> None:
        with self.sessions.begin() as session:
            item = session.scalar(select(Contract).options(joinedload(Contract.student)).where(Contract.id == contract_id))
            if item is None:
                return
            target = self.file(contract_record(item))
            session.delete(item)
        if target is not None and target.exists():
            removed = self.paths.contracts / "_removidos"
            removed.mkdir(exist_ok=True)
            target.replace(removed / target.name)
