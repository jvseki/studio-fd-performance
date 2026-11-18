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
        self.client = TestClient(create_app(Path(self.temp.name)))
        self.client.__enter__()

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

    def test_erros_viram_mensagem(self):
        self.assertEqual(self.client.post("/api/alunos", json={"full_name": " ", "phone": "1"}).status_code, 400)
        self.assertEqual(self.client.get("/api/alunos/999").status_code, 400)
        self.assertEqual(self.client.get("/api/mensalidades?mes_ref=abc").status_code, 400)


if __name__ == "__main__":
    unittest.main()
