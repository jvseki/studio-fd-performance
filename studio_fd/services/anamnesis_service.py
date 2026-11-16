"""Anamneses em PDF: cópia para data/anamneses/<aluno>/, histórico por aluno.

Garantias:
- o PDF original pode ser apagado ou movido depois: a ficha usa a cópia interna;
- a cópia é gravada antes do registro; se o banco falhar, a cópia é apagada
  (sem arquivo órfão); se a cópia falhar, nada é gravado no banco;
- remover move o arquivo para anamneses/_removidos (reversível à mão).
A checagem de formato confere extensão, tamanho e assinatura %PDF; isso NÃO é
garantia de ausência de vírus.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from studio_fd.models import Anamnesis, Student
from studio_fd.utils.paths import AppPaths

MAX_PDF_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class AnamnesisRecord:
    id: int
    student_id: int
    file_path: str
    original_name: str
    attached_on: date
    size_bytes: int
    sha256: str
    notes: str | None


def _record(item: Anamnesis) -> AnamnesisRecord:
    return AnamnesisRecord(item.id, item.student_id, item.file_path, item.original_name, item.attached_on,
                           item.size_bytes, item.sha256, item.notes)


def validate_pdf(source: Path) -> int:
    """Confere o arquivo escolhido e devolve o tamanho em bytes."""
    if source.suffix.lower() != ".pdf":
        raise ValueError("Escolha um arquivo com extensão .pdf.")
    if not source.is_file():
        raise ValueError("O arquivo escolhido não foi encontrado.")
    try:
        size = source.stat().st_size
        with source.open("rb") as reader:
            header = reader.read(5)
    except OSError as error:
        raise ValueError("Não foi possível ler o arquivo. Confira se ele está aberto em outro programa.") from error
    if size == 0:
        raise ValueError("O arquivo está vazio.")
    if size > MAX_PDF_BYTES:
        raise ValueError("O PDF passa de 50 MB. Reduza o arquivo e tente novamente.")
    if header != b"%PDF-":
        raise ValueError("O arquivo escolhido não é um PDF válido.")
    return size


class AnamnesisService:
    def __init__(self, sessions: sessionmaker[Session], paths: AppPaths):
        self.sessions = sessions
        self.paths = paths

    def for_student(self, student_id: int) -> list[AnamnesisRecord]:
        with self.sessions() as session:
            statement = (select(Anamnesis).where(Anamnesis.student_id == student_id)
                         .order_by(Anamnesis.attached_on.desc(), Anamnesis.id.desc()))
            return [_record(item) for item in session.scalars(statement)]

    def file(self, record: AnamnesisRecord) -> Path:
        root = self.paths.anamneses.resolve()
        target = (root / record.file_path).resolve()
        if not target.is_relative_to(root):
            raise ValueError("O caminho da anamnese é inválido.")
        return target

    def add(self, student_id: int, source: Path, attached_on: date | None = None, notes: str | None = None) -> AnamnesisRecord:
        source = Path(source)
        validate_pdf(source)
        attached_on = attached_on or date.today()
        if attached_on > date.today():
            raise ValueError("A data da anamnese não pode estar no futuro.")
        with self.sessions() as session:
            if session.get(Student, student_id) is None:
                raise ValueError("Esse aluno não foi encontrado.")
        folder = self.paths.anamneses / str(student_id)
        folder.mkdir(parents=True, exist_ok=True)
        name = f"anamnese_{attached_on:%Y%m%d}_{uuid4().hex}.pdf"
        target = folder / name
        partial = folder / (name + ".partial")
        digest = hashlib.sha256()
        try:
            with source.open("rb") as reader, partial.open("xb") as writer:
                for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                    digest.update(chunk)
                    writer.write(chunk)
            size = partial.stat().st_size
            partial.replace(target)
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise ValueError("Não foi possível copiar o PDF para a pasta do Studio. Confira o espaço em disco.") from error
        try:
            with self.sessions.begin() as session:
                item = Anamnesis(student_id=student_id, file_path=f"{student_id}/{name}",
                                 original_name=source.name[:255], attached_on=attached_on, size_bytes=size,
                                 sha256=digest.hexdigest(), notes=(notes or "").strip() or None)
                session.add(item)
                session.flush()
                return _record(item)
        except Exception:
            target.unlink(missing_ok=True)  # sem registro, sem arquivo
            raise

    def save_copy(self, record: AnamnesisRecord, destination: Path) -> Path:
        source = self.file(record)
        if not source.exists():
            raise ValueError("O PDF desta anamnese não está na pasta do Studio. Restaure um backup para recuperá-lo.")
        shutil.copy2(source, destination)
        return Path(destination)

    def delete(self, anamnesis_id: int) -> None:
        with self.sessions.begin() as session:
            item = session.get(Anamnesis, anamnesis_id)
            if item is None:
                return
            target = self.file(_record(item))
            session.delete(item)
        if target.exists():
            removed = self.paths.anamneses / "_removidos"
            removed.mkdir(exist_ok=True)
            target.replace(removed / target.name)
