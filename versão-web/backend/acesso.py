"""Login da versão web: usuários, senhas e sessões.

- Senhas guardadas só como hash PBKDF2-SHA256 (600 mil iterações, sal próprio).
- Sessão em cookie HttpOnly + SameSite=Lax, assinado com HMAC (SECRET_KEY).
  O navegador não deixa JavaScript ler o cookie, e sites de fora não conseguem
  enviá-lo em formulários (proteção contra CSRF), além da checagem de Origin.
- Limite de tentativas de login por e-mail e por IP.
- Tabela própria (web_usuarios), separada das tabelas do desktop.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import secrets
import time

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, func, insert, select, update
from sqlalchemy.engine import Engine

ITERACOES = 600_000
DURACAO_SESSAO = 60 * 60 * 24 * 14  # 14 dias
COOKIE = "studiofd_sessao"
PAPEIS = ("admin", "equipe")

metadata = MetaData()
usuarios = Table(
    "web_usuarios", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("nome", String(80), nullable=False),
    Column("senha_hash", String(200), nullable=False),
    Column("papel", String(10), nullable=False, default="equipe"),
    Column("ativo", Boolean, nullable=False, default=True),
    Column("versao_sessao", Integer, nullable=False, default=1),  # muda ao trocar senha: derruba sessões antigas
    Column("criado_em", DateTime(timezone=True), nullable=False),
)


@dataclass(frozen=True)
class Usuario:
    id: int
    email: str
    nome: str
    papel: str
    ativo: bool


def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return f"pbkdf2_sha256${ITERACOES}${base64.b64encode(sal).decode()}${base64.b64encode(derivado).decode()}"


def conferir_senha(senha: str, guardado: str) -> bool:
    try:
        _algoritmo, iteracoes, sal, esperado = guardado.split("$")
        derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), base64.b64decode(sal), int(iteracoes))
        return hmac.compare_digest(derivado, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False


def validar_senha(senha: str) -> None:
    if len(senha) < 8:
        raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
    if senha.isdigit() or senha.isalpha():
        raise ValueError("Use letras e números na senha.")


def normalizar_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        raise ValueError("Confira o e-mail.")
    return email


class Acesso:
    def __init__(self, engine: Engine, segredo: str):
        self.engine = engine
        self.segredo = segredo.encode("utf-8")
        metadata.create_all(engine)  # só cria a tabela se ela não existir
        self._tentativas: dict[str, list[float]] = {}

    # ------------------------------------------------------------- usuários
    def _linha(self, linha) -> Usuario:
        return Usuario(linha.id, linha.email, linha.nome, linha.papel, linha.ativo)

    def total(self) -> int:
        with self.engine.connect() as conexao:
            return conexao.scalar(select(func.count()).select_from(usuarios)) or 0

    def listar(self) -> list[Usuario]:
        with self.engine.connect() as conexao:
            return [self._linha(l) for l in conexao.execute(select(usuarios).order_by(usuarios.c.nome))]

    def criar(self, email: str, nome: str, senha: str, papel: str = "equipe") -> Usuario:
        email = normalizar_email(email)
        nome = " ".join(nome.split())[:80]
        if not nome:
            raise ValueError("Informe o nome.")
        if papel not in PAPEIS:
            raise ValueError("Papel inválido.")
        validar_senha(senha)
        with self.engine.begin() as conexao:
            if conexao.scalar(select(usuarios.c.id).where(usuarios.c.email == email)):
                raise ValueError("Já existe um usuário com esse e-mail.")
            novo = conexao.execute(insert(usuarios).values(
                email=email, nome=nome, senha_hash=gerar_hash(senha), papel=papel, ativo=True,
                versao_sessao=1, criado_em=datetime.now(timezone.utc))).inserted_primary_key[0]
        return self.buscar(novo)

    def buscar(self, usuario_id: int) -> Usuario | None:
        with self.engine.connect() as conexao:
            linha = conexao.execute(select(usuarios).where(usuarios.c.id == usuario_id)).first()
            return self._linha(linha) if linha else None

    def definir_ativo(self, usuario_id: int, ativo: bool, quem: Usuario) -> Usuario:
        if usuario_id == quem.id and not ativo:
            raise ValueError("Você não pode desativar a sua própria conta.")
        with self.engine.begin() as conexao:
            conexao.execute(update(usuarios).where(usuarios.c.id == usuario_id)
                            .values(ativo=ativo, versao_sessao=usuarios.c.versao_sessao + 1))
        usuario = self.buscar(usuario_id)
        if usuario is None:
            raise ValueError("Usuário não encontrado.")
        return usuario

    def trocar_senha(self, usuario_id: int, atual: str | None, nova: str) -> None:
        validar_senha(nova)
        with self.engine.begin() as conexao:
            linha = conexao.execute(select(usuarios).where(usuarios.c.id == usuario_id)).first()
            if linha is None:
                raise ValueError("Usuário não encontrado.")
            if atual is not None and not conferir_senha(atual, linha.senha_hash):
                raise ValueError("A senha atual não confere.")
            conexao.execute(update(usuarios).where(usuarios.c.id == usuario_id)
                            .values(senha_hash=gerar_hash(nova), versao_sessao=linha.versao_sessao + 1))

    def garantir_admin(self, email: str | None, senha: str | None) -> bool:
        """Cria o primeiro administrador se ainda não existe nenhum usuário."""
        if not email or not senha or self.total():
            return False
        self.criar(email, "Administrador", senha, "admin")
        return True

    # ------------------------------------------------------------- login
    def _bloqueado(self, chave: str) -> bool:
        agora = time.time()
        recentes = [t for t in self._tentativas.get(chave, []) if agora - t < 15 * 60]
        self._tentativas[chave] = recentes
        return len(recentes) >= 8

    def entrar(self, email: str, senha: str, ip: str) -> tuple[Usuario, str]:
        email = email.strip().lower()
        for chave in (f"e:{email}", f"i:{ip}"):
            if self._bloqueado(chave):
                raise PermissionError("Muitas tentativas. Espere 15 minutos e tente de novo.")
        with self.engine.connect() as conexao:
            linha = conexao.execute(select(usuarios).where(usuarios.c.email == email)).first()
        # Confere a senha mesmo sem usuário, para não revelar quais e-mails existem pelo tempo de resposta.
        valido = conferir_senha(senha, linha.senha_hash if linha else gerar_hash("x" * 12))
        if not linha or not valido or not linha.ativo:
            for chave in (f"e:{email}", f"i:{ip}"):
                self._tentativas.setdefault(chave, []).append(time.time())
            raise PermissionError("E-mail ou senha incorretos.")
        self._tentativas.pop(f"e:{email}", None)
        return self._linha(linha), self._assinar({"u": linha.id, "v": linha.versao_sessao, "x": int(time.time()) + DURACAO_SESSAO})

    def _assinar(self, dados: dict) -> str:
        corpo = base64.urlsafe_b64encode(json.dumps(dados, separators=(",", ":")).encode()).decode().rstrip("=")
        assinatura = hmac.new(self.segredo, corpo.encode(), hashlib.sha256).hexdigest()
        return f"{corpo}.{assinatura}"

    def sessao(self, token: str | None) -> Usuario | None:
        if not token or "." not in token:
            return None
        corpo, assinatura = token.rsplit(".", 1)
        esperado = hmac.new(self.segredo, corpo.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(assinatura, esperado):
            return None
        try:
            dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
        except ValueError:
            return None
        if dados.get("x", 0) < time.time():
            return None
        with self.engine.connect() as conexao:
            linha = conexao.execute(select(usuarios).where(usuarios.c.id == dados.get("u"))).first()
        if not linha or not linha.ativo or linha.versao_sessao != dados.get("v"):
            return None
        return self._linha(linha)


def segredo_da_aplicacao() -> str:
    segredo = os.environ.get("SECRET_KEY", "")
    if len(segredo) >= 32:
        return segredo
    if os.environ.get("DATABASE_URL"):
        raise RuntimeError("Defina SECRET_KEY (32+ caracteres aleatórios) antes de usar o banco de produção.")
    return secrets.token_hex(32)  # teste local: sessões valem só enquanto o servidor estiver ligado
