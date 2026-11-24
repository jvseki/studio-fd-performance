"""PDFs (contratos e anamneses) no Supabase Storage.

Os serviços do desktop gravam o PDF numa pasta local; aqui essa cópia é enviada
ao bucket privado do Supabase. Se o servidor reiniciar (o disco do Render grátis
é apagado), o PDF é baixado de volta na primeira vez que alguém abrir.
Sem SUPABASE_URL/SUPABASE_SERVICE_KEY, tudo fica só no disco local (testes).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import httpx


class Armazenamento:
    def __init__(self) -> None:
        self.url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.chave = os.environ.get("SUPABASE_SERVICE_KEY", "")
        self.bucket = os.environ.get("SUPABASE_BUCKET", "documentos")
        self.ativo = bool(self.url and self.chave)

    def _cabecalhos(self, tipo: str | None = None) -> dict[str, str]:
        cabecalhos = {"Authorization": f"Bearer {self.chave}", "apikey": self.chave}
        if tipo:
            cabecalhos["Content-Type"] = tipo
        return cabecalhos

    def _endereco(self, caminho: str) -> str:
        return f"{self.url}/storage/v1/object/{self.bucket}/{quote(caminho)}"

    def enviar(self, caminho: str, arquivo: Path) -> None:
        if not self.ativo:
            return
        resposta = httpx.post(self._endereco(caminho), content=arquivo.read_bytes(), timeout=60,
                              headers={**self._cabecalhos("application/pdf"), "x-upsert": "true"})
        if resposta.status_code >= 300:
            raise RuntimeError(f"Falha ao guardar o PDF no Supabase ({resposta.status_code}).")

    def baixar_se_faltar(self, caminho: str, destino: Path) -> bool:
        """Garante o PDF no disco local. Devolve False se ele não existir em lugar nenhum."""
        if destino.exists():
            return True
        if not self.ativo:
            return False
        resposta = httpx.get(self._endereco(caminho), headers=self._cabecalhos(), timeout=60)
        if resposta.status_code != 200:
            return False
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(resposta.content)
        return True

    def mover_para_removidos(self, caminho: str) -> None:
        """Mesma política do desktop: remover não apaga, guarda em _removidos."""
        if not self.ativo:
            return
        pasta, nome = caminho.split("/", 1)[0], caminho.rsplit("/", 1)[-1]
        httpx.post(f"{self.url}/storage/v1/object/move", headers=self._cabecalhos("application/json"), timeout=30,
                   json={"bucketId": self.bucket, "sourceKey": caminho, "destinationKey": f"{pasta}/_removidos/{nome}"})

    def listar(self, prefixo: str) -> list[str]:
        if not self.ativo:
            return []
        resposta = httpx.post(f"{self.url}/storage/v1/object/list/{self.bucket}", headers=self._cabecalhos("application/json"),
                              json={"prefix": prefixo, "limit": 1000}, timeout=30)
        return [item["name"] for item in resposta.json()] if resposta.status_code == 200 else []

    def baixar(self, caminho: str) -> bytes | None:
        if not self.ativo:
            return None
        resposta = httpx.get(self._endereco(caminho), headers=self._cabecalhos(), timeout=60)
        return resposta.content if resposta.status_code == 200 else None
