"""API da versão web do Studio FD Performance (FastAPI).

Reaproveita as regras da versão desktop: modelos, migrações e serviços do
pacote `studio_fd`. Nada de regra de negócio duplicada aqui; esta camada só
traduz HTTP <-> serviços.

Login obrigatório em toda a API (veja acesso.py). Banco: PostgreSQL do Supabase
quando DATABASE_URL estiver definida; senão, SQLite local (testes e demonstração).

Rodar:  ..\\..\\.venv\\Scripts\\python.exe -m uvicorn app:app --reload --port 8000
"""


from contextlib import asynccontextmanager
from datetime import date
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.responses import Response as RespostaBruta  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from studio_fd import __version__  # noqa: E402
from studio_fd.database.migrations import migrate_database  # noqa: E402
from studio_fd.database.session import create_database_engine, create_engine_from_url, create_session_factory  # noqa: E402
from studio_fd.models import Anamnesis  # noqa: E402
from studio_fd.services.agenda_service import AgendaService  # noqa: E402
from studio_fd.services.anamnesis_service import AnamnesisService  # noqa: E402
from studio_fd.services.backup_service import BackupService  # noqa: E402
from studio_fd.services.cash_service import EXPENSE_CATEGORIES, INCOME_CATEGORIES, CashService  # noqa: E402
from studio_fd.services.contract_service import ContractService  # noqa: E402
from studio_fd.services.dashboard_service import DashboardService  # noqa: E402
from studio_fd.services.finance_service import FinanceService  # noqa: E402
from studio_fd.services.plan_service import PlanService  # noqa: E402
from studio_fd.services.records import CashInput, PlanInput, StudentInput  # noqa: E402
from studio_fd.services.report_service import ReportService  # noqa: E402
from studio_fd.services.settings_service import SettingsService  # noqa: E402
from studio_fd.services.student_service import StudentService  # noqa: E402
from studio_fd.utils.dates import add_months, first_of_month  # noqa: E402
from studio_fd.utils.paths import AppPaths  # noqa: E402

import backup_web  # noqa: E402
from acesso import COOKIE, DURACAO_SESSAO, Acesso, Usuario, segredo_da_aplicacao  # noqa: E402
from armazenamento import Armazenamento  # noqa: E402

# Pasta de dados própria da versão web: NUNCA a pasta do desktop por padrão.
DATA_DIR = Path(os.environ.get("STUDIO_FD_WEB_DATA", Path(__file__).resolve().parent / "dados"))


class Services:
    def __init__(self, paths: AppPaths, database_url: str | None = None):
        paths.ensure_directories()
        self.paths = paths
        self.postgres = bool(database_url)
        # PDFs ficam na pasta local (cópia de trabalho) e, com Supabase, também no Storage.
        self.engine = create_engine_from_url(database_url) if database_url else create_database_engine(paths.database)
        migrate_database(self.engine)
        sessions = create_session_factory(self.engine)
        self.dashboard = DashboardService(sessions)
        self.students = StudentService(sessions)
        self.plans = PlanService(sessions)
        self.settings = SettingsService(sessions)
        self.agenda = AgendaService(sessions)
        self.finance = FinanceService(sessions)
        self.cash = CashService(sessions)
        self.contracts = ContractService(sessions, paths)
        self.anamneses = AnamnesisService(sessions, paths)
        self.reports = ReportService(sessions)
        self.backup = BackupService(paths, __version__)
        self.storage = Armazenamento()
        self.acesso = Acesso(self.engine, segredo_da_aplicacao())
        self.acesso.garantir_admin(os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_SENHA_INICIAL"))


ROTAS_PUBLICAS = {"/api/saude", "/api/entrar", "/api/sair"}


def create_app(data_dir: Path = DATA_DIR, database_url: str | None = None) -> FastAPI:
    database_url = database_url if database_url is not None else os.environ.get("DATABASE_URL") or None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.s = Services(AppPaths(Path(data_dir)), database_url)
        yield
        app.state.s.engine.dispose()

    app = FastAPI(title="Studio FD Performance", version=__version__, lifespan=lifespan)

    @app.exception_handler(ValueError)
    async def regra_de_negocio(_request: Request, error: ValueError):
        # Os serviços sinalizam regras violadas com ValueError e mensagem pronta para o usuário.
        return JSONResponse(status_code=400, content={"detail": str(error)})

    s = lambda request: request.app.state.s  # noqa: E731

    # ------------------------------------------------------------- login em toda a API
    @app.middleware("http")
    async def exigir_login(request: Request, chamar_proxima):
        caminho = request.url.path
        if caminho.startswith("/api/") and caminho not in ROTAS_PUBLICAS:
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                origem = request.headers.get("origin")
                if origem and origem.split("://", 1)[-1] != request.headers.get("host"):
                    return JSONResponse(status_code=403, content={"detail": "Origem não permitida."})
            usuario = request.app.state.s.acesso.sessao(request.cookies.get(COOKIE))
            if usuario is None:
                return JSONResponse(status_code=401, content={"detail": "Entre com seu e-mail e senha."})
            request.state.usuario = usuario
        return await chamar_proxima(request)

    def usuario(request: Request) -> Usuario:
        return request.state.usuario

    def exigir_admin(request: Request) -> Usuario:
        quem = usuario(request)
        if quem.papel != "admin":
            raise HTTPException(403, "Somente o administrador pode fazer isso.")
        return quem

    class EntrarIn(BaseModel):
        email: str
        senha: str

    class SenhaIn(BaseModel):
        atual: str | None = None
        nova: str

    class UsuarioIn(BaseModel):
        nome: str
        email: str
        senha: str
        papel: str = "equipe"

    class AtivoIn(BaseModel):
        ativo: bool

    @app.post("/api/entrar")
    def entrar(request: Request, response: Response, body: EntrarIn):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
        try:
            quem, token = s(request).acesso.entrar(body.email, body.senha, ip)
        except PermissionError as erro:
            raise HTTPException(401, str(erro)) from erro
        https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(COOKIE, token, max_age=DURACAO_SESSAO, httponly=True, secure=https, samesite="lax", path="/")
        return quem

    @app.post("/api/sair")
    def sair(response: Response):
        response.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.get("/api/eu")
    def eu(request: Request):
        return usuario(request)

    @app.post("/api/eu/senha")
    def trocar_minha_senha(request: Request, response: Response, body: SenhaIn):
        quem = usuario(request)
        s(request).acesso.trocar_senha(quem.id, body.atual or "", body.nova)
        response.delete_cookie(COOKIE, path="/")  # a sessão antiga deixa de valer; entra de novo com a senha nova
        return {"ok": True}

    @app.get("/api/usuarios")
    def listar_usuarios(request: Request):
        exigir_admin(request)
        return s(request).acesso.listar()

    @app.post("/api/usuarios")
    def criar_usuario(request: Request, body: UsuarioIn):
        exigir_admin(request)
        return s(request).acesso.criar(body.email, body.nome, body.senha, body.papel)

    @app.patch("/api/usuarios/{usuario_id}")
    def ativar_usuario(request: Request, usuario_id: int, body: AtivoIn):
        return s(request).acesso.definir_ativo(usuario_id, body.ativo, exigir_admin(request))

    @app.post("/api/usuarios/{usuario_id}/senha")
    def redefinir_senha(request: Request, usuario_id: int, body: SenhaIn):
        exigir_admin(request)
        s(request).acesso.trocar_senha(usuario_id, None, body.nova)
        return {"ok": True}

    # ------------------------------------------------------------- geral
    @app.get("/api/saude")
    def saude():
        return {"ok": True, "versao": __version__}

    @app.get("/api/resumo")
    def resumo(request: Request):
        return s(request).dashboard.summary()

    # ------------------------------------------------------------- planos
    class PlanoIn(BaseModel):
        name: str
        workouts_per_week: int = Field(ge=1, le=7)
        price_cents: int = Field(ge=0)
        duration_months: int = Field(default=1, ge=1, le=120)
        description: str | None = None
        active: bool = True

    @app.get("/api/planos")
    def planos(request: Request):
        return s(request).plans.list()

    @app.post("/api/planos")
    def criar_plano(request: Request, body: PlanoIn):
        return s(request).plans.save(PlanInput(**body.model_dump()))

    @app.put("/api/planos/{plan_id}")
    def editar_plano(request: Request, plan_id: int, body: PlanoIn):
        return s(request).plans.save(PlanInput(**body.model_dump()), plan_id)

    # ------------------------------------------------------------- alunos
    class AlunoIn(BaseModel):
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

    @app.get("/api/alunos")
    def alunos(request: Request, q: str = "", letra: str = "", ativo: bool | None = None):
        return s(request).students.list(q, letra, ativo)

    @app.get("/api/alunos/{student_id}")
    def aluno(request: Request, student_id: int):
        services = s(request)
        return {
            "aluno": services.students.get(student_id),
            "horarios_fixos": services.agenda.habitual(student_id),
            "proximos": services.agenda.for_student(student_id, date.today(), 14),
            "mensalidades": services.finance.for_student(student_id),
            "contratos": services.contracts.for_student(student_id),
            "anamneses": services.anamneses.for_student(student_id),
        }

    @app.post("/api/alunos")
    def criar_aluno(request: Request, body: AlunoIn):
        return s(request).students.save(StudentInput(**body.model_dump()))

    @app.put("/api/alunos/{student_id}")
    def editar_aluno(request: Request, student_id: int, body: AlunoIn):
        return s(request).students.save(StudentInput(**body.model_dump()), student_id)

    # ------------------------------------------------------------- configurações
    class PersonalIn(BaseModel):
        name: str
        active: bool = True

    class HorarioIn(BaseModel):
        open_time: str
        close_time: str
        slot_minutes: int

    @app.get("/api/configuracoes")
    def configuracoes(request: Request):
        services = s(request)
        hours = services.settings.hours()
        return {"personais": services.settings.trainers(), "horario": hours, "horarios": hours.slots(),
                "categorias_entrada": INCOME_CATEGORIES, "categorias_saida": EXPENSE_CATEGORIES}

    @app.post("/api/personais")
    def criar_personal(request: Request, body: PersonalIn):
        return s(request).settings.save_trainer(body.name, body.active)

    @app.put("/api/personais/{trainer_id}")
    def editar_personal(request: Request, trainer_id: int, body: PersonalIn):
        return s(request).settings.save_trainer(body.name, body.active, trainer_id)

    @app.put("/api/horario")
    def editar_horario(request: Request, body: HorarioIn):
        return s(request).settings.save_hours(body.open_time, body.close_time, body.slot_minutes)

    # ------------------------------------------------------------- agenda
    class AgendamentoIn(BaseModel):
        student_id: int
        day: date
        time: str
        trainer_id: int | None = None
        repeat_weeks: int = Field(default=0, ge=0, le=52)
        notes: str | None = None

    class SituacaoIn(BaseModel):
        status: str

    @app.get("/api/agenda")
    def agenda(request: Request, dia: date | None = None):
        services = s(request)
        day = dia or date.today()
        start = day.fromordinal(day.toordinal() - day.weekday())
        week = services.agenda.occupancy(start)
        return {"dia": day, "linhas": services.agenda.day(day),
                "semana": [{"dia": d, "ocupadas": used, "vagas": total} for d, (used, total) in week.items()]}

    @app.post("/api/agenda")
    def agendar(request: Request, body: AgendamentoIn):
        return s(request).agenda.book(body.student_id, body.day, body.time, body.trainer_id, body.repeat_weeks, body.notes)

    @app.patch("/api/agenda/{appointment_id}")
    def situacao(request: Request, appointment_id: int, body: SituacaoIn):
        s(request).agenda.set_status(appointment_id, body.status)
        return {"ok": True}

    @app.delete("/api/agenda/{appointment_id}")
    def desmarcar(request: Request, appointment_id: int, serie: bool = False):
        services = s(request)
        if serie:
            return {"removidos": services.agenda.remove_future_series(appointment_id)}
        services.agenda.remove(appointment_id)
        return {"removidos": 1}

    # ------------------------------------------------------------- mensalidades
    class AvulsaIn(BaseModel):
        student_id: int
        month: date
        amount_cents: int
        due_date: date
        notes: str | None = None

    class PagamentoIn(BaseModel):
        paid_on: date
        method: str
        amount_cents: int | None = None

    def mes(valor: str | None) -> date:
        if not valor:
            return first_of_month(date.today())
        try:
            year, month = (int(part) for part in valor.split("-")[:2])
            return date(year, month, 1)
        except ValueError as error:
            raise ValueError("Use o mês no formato AAAA-MM.") from error

    @app.get("/api/mensalidades")
    def mensalidades(request: Request, mes_ref: str | None = None):
        services = s(request)
        month = mes(mes_ref)
        return {"mes": month, "lista": services.finance.month(month), "resumo": services.finance.summary(month)}

    @app.post("/api/mensalidades/gerar")
    def gerar(request: Request, mes_ref: str | None = None):
        return {"geradas": s(request).finance.generate(mes(mes_ref))}

    @app.post("/api/mensalidades")
    def avulsa(request: Request, body: AvulsaIn):
        s(request).finance.add(body.student_id, body.month, body.amount_cents, body.due_date, body.notes)
        return {"ok": True}

    @app.post("/api/mensalidades/{payment_id}/pagar")
    def pagar(request: Request, payment_id: int, body: PagamentoIn):
        s(request).finance.register(payment_id, body.paid_on, body.method, body.amount_cents)
        return {"ok": True}

    @app.post("/api/mensalidades/{payment_id}/desfazer")
    def desfazer(request: Request, payment_id: int):
        s(request).finance.undo(payment_id)
        return {"ok": True}

    @app.delete("/api/mensalidades/{payment_id}")
    def excluir_mensalidade(request: Request, payment_id: int):
        s(request).finance.delete(payment_id)
        return {"ok": True}

    # ------------------------------------------------------------- caixa
    class MovimentoIn(BaseModel):
        day: date
        description: str
        category: str
        kind: str
        amount_cents: int
        method: str | None = None
        notes: str | None = None

    @app.get("/api/caixa")
    def caixa(request: Request, inicio: date | None = None, fim: date | None = None):
        start = inicio or date.today()
        end = fim or start
        services = s(request)
        totals = services.cash.totals(start, end)
        return {"lista": services.cash.entries(start, end),
                "entradas": totals.income_cents, "saidas": totals.expense_cents, "saldo": totals.balance_cents}

    @app.post("/api/caixa")
    def lancar(request: Request, body: MovimentoIn):
        return s(request).cash.add(CashInput(**body.model_dump()))

    @app.delete("/api/caixa/{entry_id}")
    def excluir_movimento(request: Request, entry_id: int):
        s(request).cash.delete(entry_id)
        return {"ok": True}

    # ------------------------------------------------------------- PDFs
    def guardar_upload(arquivo: UploadFile, pasta: Path) -> Path:
        destino = pasta / Path(arquivo.filename or "documento.pdf").name
        with destino.open("wb") as saida:
            shutil.copyfileobj(arquivo.file, saida)
        return destino

    @app.get("/api/contratos")
    def contratos(request: Request, q: str = ""):
        return s(request).contracts.list(q)

    @app.post("/api/contratos")
    def anexar_contrato(request: Request, student_id: int = Form(...), signature_type: str = Form(...),
                        signed_on: date = Form(...), notes: str | None = Form(None), arquivo: UploadFile | None = File(None)):
        with TemporaryDirectory() as pasta:
            pdf = guardar_upload(arquivo, Path(pasta)) if arquivo else None
            services = s(request)
            record = services.contracts.add(student_id, signature_type, signed_on, pdf, notes)
            if record.file_path:
                services.storage.enviar(f"contratos/{record.file_path}", services.contracts.file(record))
            return record

    @app.get("/api/contratos/{contract_id}/arquivo")
    def arquivo_contrato(request: Request, contract_id: int):
        services = s(request)
        record = next((item for item in services.contracts.list() if item.id == contract_id), None)
        target = services.contracts.file(record) if record and record.file_path else None
        if target is None or not services.storage.baixar_se_faltar(f"contratos/{record.file_path}", target):
            raise HTTPException(404, "Este contrato não tem PDF.")
        return FileResponse(target, media_type="application/pdf")

    @app.delete("/api/contratos/{contract_id}")
    def excluir_contrato(request: Request, contract_id: int):
        services = s(request)
        record = next((item for item in services.contracts.list() if item.id == contract_id), None)
        services.contracts.delete(contract_id)
        if record and record.file_path:
            services.storage.mover_para_removidos(f"contratos/{record.file_path}")
        return {"ok": True}

    @app.post("/api/alunos/{student_id}/anamneses")
    def anexar_anamnese(request: Request, student_id: int, arquivo: UploadFile = File(...),
                        attached_on: date | None = Form(None), notes: str | None = Form(None)):
        with TemporaryDirectory() as pasta:
            services = s(request)
            record = services.anamneses.add(student_id, guardar_upload(arquivo, Path(pasta)), attached_on, notes)
            try:
                services.storage.enviar(f"anamneses/{record.file_path}", services.anamneses.file(record))
            except Exception:
                services.anamneses.delete(record.id)  # sem cópia segura na nuvem, não fica registro pela metade
                raise HTTPException(502, "Não foi possível guardar o PDF agora. Tente de novo.")
            return record

    @app.get("/api/anamneses/{anamnesis_id}/arquivo")
    def arquivo_anamnese(request: Request, anamnesis_id: int, student_id: int):
        services = s(request)
        record = next((item for item in services.anamneses.for_student(student_id) if item.id == anamnesis_id), None)
        if record is None or not services.storage.baixar_se_faltar(f"anamneses/{record.file_path}", services.anamneses.file(record)):
            raise HTTPException(404, "PDF da anamnese não encontrado.")
        return FileResponse(services.anamneses.file(record), media_type="application/pdf", filename=record.original_name)

    @app.delete("/api/anamneses/{anamnesis_id}")
    def excluir_anamnese(request: Request, anamnesis_id: int):
        services = s(request)
        with services.engine.connect() as conexao:
            caminho = conexao.scalar(Anamnesis.__table__.select().with_only_columns(Anamnesis.file_path).where(Anamnesis.id == anamnesis_id))
        services.anamneses.delete(anamnesis_id)
        if caminho:
            services.storage.mover_para_removidos(f"anamneses/{caminho}")
        return {"ok": True}

    # ------------------------------------------------------------- relatórios e backup
    @app.get("/api/relatorios")
    def relatorios(request: Request, mes_ref: str | None = None):
        return s(request).reports.build(mes(mes_ref))

    @app.get("/api/backup")
    def backup(request: Request):
        services = s(request)
        if services.postgres:  # banco na nuvem: dados em JSON + PDFs num .zip
            nome, conteudo = backup_web.exportar(services.engine, {"contratos": services.paths.contracts, "anamneses": services.paths.anamneses}, services.storage)
            return RespostaBruta(conteudo, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{nome}"'})
        target = services.backup.export(services.paths.backups / services.backup.default_name(), reason="manual")
        return FileResponse(target, media_type="application/zip", filename=target.name)

    # Mês anterior/seguinte para a navegação do front (evita reimplementar calendário).
    @app.get("/api/meses")
    def meses(mes_ref: str | None = None):
        month = mes(mes_ref)
        return {"anterior": add_months(month, -1), "atual": month, "seguinte": add_months(month, 1)}

    # Site pronto (npm run build): o mesmo servidor entrega as telas, num endereço só.
    site = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if site.is_dir():
        app.mount("/assets", StaticFiles(directory=site / "assets"), name="assets")

        @app.get("/{caminho:path}", include_in_schema=False)
        def telas(caminho: str):
            if caminho.startswith("api/"):
                raise HTTPException(404, "Endereço da API não encontrado.")
            arquivo = (site / caminho).resolve()
            if caminho and arquivo.is_file() and arquivo.is_relative_to(site.resolve()):
                return FileResponse(arquivo)
            return FileResponse(site / "index.html")  # rotas do React (/agenda, /alunos...)

    return app


app = create_app()
