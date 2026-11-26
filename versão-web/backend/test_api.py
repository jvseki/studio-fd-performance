"""Testes da API com dados fictícios em pasta temporária.
Rodar:  ..\\..\\.venv\\Scripts\\python.exe -m unittest test_api -v
"""

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.client = TestClient(create_app(Path(self.temp.name), database_url=""))
        self.client.__enter__()
        self.client.app.state.s.acesso.criar("admin@teste.com", "Admin", "senha-forte-1", "admin")
        self.assertEqual(self.client.post("/api/entrar", json={"email": "admin@teste.com", "senha": "senha-forte-1"}).status_code, 200)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def aluno(self, nome, **extra):
        response = self.client.post("/api/alunos", json={"full_name": nome, "phone": "18999999999", **extra})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["id"]

    def test_fluxo_completo(self):
        plano = self.client.post("/api/planos", json={"name": "Individual 3x", "workouts_per_week": 3, "price_cents": 45000}).json()
        ids = [self.aluno(n, plan_id=plano["id"], monthly_fee_cents=45000, due_day=5) for n in ("Ana", "Bruno", "Carla")]
        dia = date.today() + timedelta(days=1)
        for i in ids[:2]:
            self.assertEqual(self.client.post("/api/agenda", json={"student_id": i, "day": str(dia), "time": "07:00"}).status_code, 200)
        limite = self.client.post("/api/agenda", json={"student_id": ids[2], "day": str(dia), "time": "07:00"})
        self.assertEqual(limite.status_code, 400)
        self.assertIn("limite de 2 alunos", limite.json()["detail"])
        linhas = self.client.get(f"/api/agenda?dia={dia}").json()["linhas"]
        self.assertEqual(sum(1 for c in next(l for l in linhas if l["time"] == "07:00")["cells"] if c[1]), 2)

        mes = date.today().strftime("%Y-%m")
        self.assertEqual(self.client.post(f"/api/mensalidades/gerar?mes_ref={mes}").json()["geradas"], 3)
        lista = self.client.get(f"/api/mensalidades?mes_ref={mes}").json()["lista"]
        pago = self.client.post(f"/api/mensalidades/{lista[0]['id']}/pagar", json={"paid_on": str(date.today()), "method": "Pix"})
        self.assertEqual(pago.status_code, 200, pago.text)
        caixa = self.client.get("/api/caixa").json()
        self.assertEqual(caixa["entradas"], 45000)
        self.assertEqual(self.client.get("/api/resumo").json()["active_students"], 3)

    def test_pdf_e_backup(self):
        aluno = self.aluno("Diego")
        pdf = b"%PDF-1.4 ficticio"
        anexo = self.client.post(f"/api/alunos/{aluno}/anamneses", files={"arquivo": ("anamnese.pdf", pdf, "application/pdf")}, data={"notes": "Inicial"})
        self.assertEqual(anexo.status_code, 200, anexo.text)
        baixado = self.client.get(f"/api/anamneses/{anexo.json()['id']}/arquivo?student_id={aluno}")
        self.assertEqual(baixado.content, pdf)
        falso = self.client.post(f"/api/alunos/{aluno}/anamneses", files={"arquivo": ("x.pdf", b"nao e pdf", "application/pdf")})
        self.assertEqual(falso.status_code, 400)
        contrato = self.client.post("/api/contratos", data={"student_id": aluno, "signature_type": "presencial", "signed_on": str(date.today())},
                                    files={"arquivo": ("c.pdf", pdf, "application/pdf")})
        self.assertEqual(contrato.status_code, 200, contrato.text)
        self.assertEqual(self.client.get(f"/api/contratos/{contrato.json()['id']}/arquivo").content, pdf)
        ficha = self.client.get(f"/api/alunos/{aluno}").json()
        self.assertEqual((len(ficha["anamneses"]), len(ficha["contratos"])), (1, 1))
        backup = self.client.get("/api/backup")
        self.assertEqual(backup.status_code, 200)
        self.assertTrue(backup.content.startswith(b"PK"))

    def test_backup_web_abre_no_programa_do_computador(self):
        import backup_web
        from studio_fd.services.backup_service import BackupService
        from studio_fd.utils.paths import AppPaths
        services = self.client.app.state.s
        aluno = self.aluno("Elisa", birth_date="1990-03-04")
        self.client.post(f"/api/alunos/{aluno}/anamneses", files={"arquivo": ("a.pdf", b"%PDF-1.4 ficticio", "application/pdf")})
        nome, conteudo = backup_web.exportar(services.engine, {"contratos": services.paths.contracts, "anamneses": services.paths.anamneses}, services.storage)
        self.assertTrue(nome.endswith(".fdbkp"))
        arquivo = Path(self.temp.name) / nome
        arquivo.write_bytes(conteudo)
        computador = AppPaths(Path(self.temp.name) / "computador")
        computador.ensure_directories()
        info = BackupService(computador, "teste").inspect(arquivo)
        self.assertEqual((info.counts["alunos"], info.counts["anamneses"]), (1, 1))
        # restaura como o programa do computador faz: prepara, e aplica na próxima abertura
        from studio_fd.database.migrations import migrate_database
        from studio_fd.database.session import create_database_engine
        vazio = create_database_engine(computador.database)
        migrate_database(vazio)
        vazio.dispose()
        BackupService(computador, "teste").stage_restore(arquivo)
        self.assertTrue(BackupService.apply_pending(computador))
        restaurado = create_database_engine(computador.database)
        with restaurado.connect() as conexao:
            self.assertEqual(conexao.exec_driver_sql("SELECT full_name, birth_date FROM students").all(), [("Elisa", "1990-03-04")])
        restaurado.dispose()
        self.assertEqual(len(list(computador.anamneses.rglob("*.pdf"))), 1)

    def test_aniversario_no_resumo(self):
        hoje = date.today()
        nascimento = hoje.replace(year=2000)  # 2000 é bissexto: vale até em 29/02
        self.aluno("Fabi", birth_date=str(nascimento))
        self.aluno("Gui", birth_date=str((hoje + timedelta(days=1)).replace(year=2000)))
        lista = self.client.get("/api/resumo").json()["birthdays"]
        self.assertEqual([(p["name"], p["age"]) for p in lista], [("Fabi", hoje.year - 2000)])
        self.assertIn("wa.me/55", lista[0]["whatsapp_url"])

    def test_erros_viram_mensagem(self):
        self.assertEqual(self.client.post("/api/alunos", json={"full_name": " ", "phone": "1"}).status_code, 400)
        self.assertEqual(self.client.get("/api/alunos/999").status_code, 400)
        self.assertEqual(self.client.get("/api/mensalidades?mes_ref=abc").status_code, 400)


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.client = TestClient(create_app(Path(self.temp.name), database_url=""))
        self.client.__enter__()
        self.acesso = self.client.app.state.s.acesso
        self.acesso.criar("admin@teste.com", "Admin", "senha-forte-1", "admin")

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def entrar(self, email, senha):
        return self.client.post("/api/entrar", json={"email": email, "senha": senha})

    def test_api_fechada_sem_login(self):
        self.assertEqual(self.client.get("/api/alunos").status_code, 401)
        self.assertEqual(self.client.get("/api/saude").status_code, 200)
        self.assertEqual(self.entrar("admin@teste.com", "errada-123").status_code, 401)
        self.assertEqual(self.entrar("ninguem@teste.com", "senha-forte-1").status_code, 401)
        self.assertEqual(self.client.get("/api/alunos").status_code, 401)

    def test_admin_cria_equipe_e_equipe_nao_administra(self):
        self.assertEqual(self.entrar("ADMIN@teste.com ", "senha-forte-1").status_code, 200)
        self.assertEqual(self.client.get("/api/eu").json()["papel"], "admin")
        fraca = self.client.post("/api/usuarios", json={"nome": "Fran", "email": "fran@teste.com", "senha": "123"})
        self.assertEqual(fraca.status_code, 400)
        fran = self.client.post("/api/usuarios", json={"nome": "Fran", "email": "fran@teste.com", "senha": "fran-senha-1"})
        self.assertEqual(fran.status_code, 200, fran.text)
        self.client.post("/api/sair")
        self.assertEqual(self.entrar("fran@teste.com", "fran-senha-1").status_code, 200)
        self.assertEqual(self.client.get("/api/alunos").status_code, 200)
        self.assertEqual(self.client.get("/api/usuarios").status_code, 403)

    def test_trocar_senha_derruba_sessao_e_desativado_nao_entra(self):
        self.entrar("admin@teste.com", "senha-forte-1")
        antigo = self.client.cookies.get("studiofd_sessao")
        self.assertEqual(self.client.post("/api/eu/senha", json={"atual": "errada-1", "nova": "nova-senha-2"}).status_code, 400)
        self.assertEqual(self.client.post("/api/eu/senha", json={"atual": "senha-forte-1", "nova": "nova-senha-2"}).status_code, 200)
        self.client.cookies.set("studiofd_sessao", antigo)
        self.assertEqual(self.client.get("/api/alunos").status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.entrar("admin@teste.com", "nova-senha-2").status_code, 200)
        equipe = self.acesso.criar("douglas@teste.com", "Douglas", "douglas-senha-1")
        self.assertEqual(self.client.patch(f"/api/usuarios/{equipe.id}", json={"ativo": False}).status_code, 200)
        self.client.post("/api/sair")
        self.assertEqual(self.entrar("douglas@teste.com", "douglas-senha-1").status_code, 401)

    def test_pedido_de_outro_site_recusado(self):
        self.entrar("admin@teste.com", "senha-forte-1")
        r = self.client.post("/api/planos", headers={"origin": "https://site-malicioso.com"},
                             json={"name": "X", "workouts_per_week": 1, "price_cents": 1})
        self.assertEqual(r.status_code, 403)

    def test_limite_de_tentativas(self):
        for _ in range(8):
            self.entrar("admin@teste.com", "errada-123")
        self.assertIn("Muitas tentativas", self.entrar("admin@teste.com", "senha-forte-1").json()["detail"])


if __name__ == "__main__":
    unittest.main()
