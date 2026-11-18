# Studio FD Performance — versão web 1.0

Sistema de gestão do Studio no navegador, pensado primeiro para celular e tablet.
Usa **as mesmas regras da versão desktop** (agenda com limite por horário,
mensalidades, caixa, contratos, anamneses, backup).

- `backend/` — Python + FastAPI. Reaproveita o pacote `studio_fd` (mesmos modelos,
  migrações e serviços). Também entrega as telas prontas.
- `frontend/` — React + TypeScript (Vite). Menu preto e dourado, conteúdo claro,
  barra de navegação embaixo no celular, formulários que sobem de baixo.

> **Primeira versão SEM login.** Use só na rede do Studio. Antes de colocar na
> internet, o login é obrigatório (veja "Colocar na internet").

## Rodar no computador (desenvolvimento)

```powershell
# backend (porta 8000), com dados de demonstração fictícios
cd "C:\Studio performance\versão-web\backend"
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\..\.venv\Scripts\python.exe semear_demo.py dados-demo
$env:STUDIO_FD_WEB_DATA = "$PWD\dados-demo"
..\..\.venv\Scripts\python.exe -m uvicorn app:app --reload --port 8000

# frontend (porta 5190), em outro terminal
cd "C:\Studio performance\versão-web\frontend"
npm install
npm run dev
```

Abra http://localhost:5190. Testes do backend: `..\..\.venv\Scripts\python.exe -m unittest test_api`.
Fotos de conferência (celular e computador): `node tools/fotos.mjs ../conferencia`.

Os dados ficam em `backend/dados/` (ou na pasta de `STUDIO_FD_WEB_DATA`), **separados
do desktop**. Essas pastas não vão para o Git.

## Usar no Studio de graça, hoje (sem internet, sem servidor pago)

1. No computador do Studio: `cd frontend`, `npm install`, `npm run build` (uma vez).
2. Dê dois cliques em **`Iniciar versao web.cmd`**. Deixe a janela aberta.
3. No próprio computador: http://localhost:8000
4. No **tablet ou celular, no mesmo Wi-Fi**: descubra o IP do computador
   (`ipconfig` → "Endereço IPv4", por exemplo 192.168.0.15) e abra
   `http://192.168.0.15:8000`. Se não abrir, permita o Python no Firewall do Windows
   quando ele perguntar (rede **privada**).
5. No tablet: menu do navegador → **Adicionar à tela inicial**. Vira um ícone.

Custo: zero. Limite: só funciona com o computador ligado e na mesma rede.

## Colocar na internet de graça (próxima etapa)

Para acessar de qualquer lugar, o caminho gratuito previsto é:

| Parte | Serviço (plano grátis) | Observação |
|---|---|---|
| Banco de dados | Supabase (PostgreSQL, região São Paulo) | ~500 MB; pausa se ficar ~1 semana sem uso |
| Arquivos (PDFs) | Supabase Storage | ~1 GB |
| Backend Python | Render (Free Web Service) | "dorme" sem uso e demora alguns segundos para acordar |
| Site | Cloudflare Pages | grátis, HTTPS automático |

Confira os limites atuais em cada site; eles mudam.

**O que ainda precisa ser feito no código antes disso:**
1. **Login** (Douglas e Fran) e proteção de todas as rotas da API.
2. Banco PostgreSQL: hoje o backend usa SQLite e uma função de busca própria
   do SQLite (`search_key`); precisa de adaptação para Postgres.
3. PDFs no Supabase Storage: no Render grátis, os arquivos salvos no disco
   **somem** quando o serviço reinicia.
4. Backup semanal baixado e guardado fora (o plano grátis não garante backup restaurável).

Contas em nome e e-mail do **Studio**; você entra como colaborador. Nunca coloque
chaves secretas no frontend nem no Git.
