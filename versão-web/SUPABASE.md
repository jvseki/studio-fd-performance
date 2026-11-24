# Banco de dados no Supabase — passo a passo

Guia para colocar a versão web do Studio FD Performance para funcionar com dados
de verdade, que **não somem** quando o servidor reinicia. Tempo: uns 20 minutos.

> **Regra de ouro:** senhas e chaves **nunca** vão para o GitHub, para o código
> ou para conversas. Elas ficam só no arquivo `backend/.env` do seu computador e
> no painel do Render.

---

## 1. Criar o projeto

1. Entre em **https://supabase.com** → **Start your project** (de preferência com o e-mail do Studio).
2. **New project**:
   - **Name:** `studio-fd`
   - **Database Password:** clique em *Generate a password* e **guarde** (gerenciador de senhas).
     Esta é a senha do **banco**, não a do login no sistema.
   - **Region:** **South America (São Paulo)**
   - Plano **Free**
3. **Create new project** e espere uns 2 minutos.

## 2. Criar as tabelas

Escolha **um** dos caminhos:

### Caminho A — automático (recomendado)
Não precisa fazer nada. Na primeira vez que o sistema liga com o `DATABASE_URL`
preenchido (passo 5), ele cria todas as tabelas, a proteção de segurança e o
primeiro administrador.

### Caminho B — à mão, pelo SQL Editor
1. No Supabase, menu lateral → **SQL Editor** → **New query**.
2. Abra o arquivo [`supabase/criar_tabelas.sql`](supabase/criar_tabelas.sql) no VS Code,
   copie **tudo**, cole no editor e clique em **Run**.
3. Deve aparecer *Success. No rows returned*. Em **Table Editor** você verá 11 tabelas:
   `plans`, `students`, `trainers`, `settings`, `appointments`, `payments`,
   `cash_entries`, `contracts`, `anamneses`, `web_usuarios` e `alembic_version`.

> Rode o `criar_tabelas.sql` **uma vez só**, num projeto vazio. Se rodar de novo, ele dá
> erro dizendo que as tabelas já existem — isso não estraga nada.

### Dados iniciais do Studio (opcional, nos dois caminhos)
Depois que as tabelas existirem: **SQL Editor** → **New query** → cole o conteúdo de
[`supabase/dados_iniciais.sql`](supabase/dados_iniciais.sql) → **Run**.
Ele coloca **Douglas** e **Fran** como personais e cria os 6 planos
(Individual 2x a 5x e Casal 2x/3x). Pode rodar mais de uma vez sem duplicar.

### O que é a "proteção" (RLS)
O Supabase cria uma API automática para todas as tabelas. O sistema **não usa** essa API,
então todas as tabelas ficam com **RLS ligado e nenhuma regra de acesso**: ninguém lê
nada por ela. O sistema acessa como dono das tabelas e funciona normalmente.
Se o Supabase mostrar o aviso "RLS enabled, no policies", é exatamente isso que queremos.

## 3. Criar o lugar dos PDFs

1. Menu lateral → **Storage** → **New bucket**.
2. **Name:** `documentos` · **Public bucket: desligado** (anamneses são dados de saúde).
3. **Create**.

## 4. Pegar o endereço do banco e as chaves

1. **Endereço do banco:** botão **Connect** (no topo) → **Connection String** → **Session pooler**.
   Copie o endereço (`postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-...pooler.supabase.com:5432/postgres`)
   e troque **`[YOUR-PASSWORD]`** pela senha do banco do passo 1.
   > Use o **Session pooler**. A conexão "Direct" não funciona no Render (ele não tem IPv6).
2. **Chaves:** ⚙️ **Project Settings** → **API** (ou **API Keys**):
   - **Project URL** (`https://xxxx.supabase.co`)
   - chave secreta **service_role** (ou **secret**) — ⚠️ a mais perigosa: dá acesso total.

## 5. Colocar as chaves no seu computador (para testar)

1. Em `C:\Studio performance\versão-web\backend`, copie `.env.example` e renomeie a cópia para **`.env`**.
2. Preencha:

   | Campo | O que colar |
   |---|---|
   | `DATABASE_URL` | endereço do Session pooler (passo 4.1) |
   | `SUPABASE_URL` | Project URL |
   | `SUPABASE_SERVICE_KEY` | chave service_role/secret |
   | `SECRET_KEY` | 64 letras e números aleatórios (veja abaixo) |
   | `ADMIN_EMAIL` | o seu e-mail |
   | `ADMIN_SENHA_INICIAL` | a sua senha (8+ caracteres, letras e números) |

   Para gerar a `SECRET_KEY`, rode no terminal do VS Code:
   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Salve. O `.env` **não** vai para o GitHub (já está protegido no `.gitignore`).

## 6. Colocar as chaves no Render (o site de verdade)

1. **https://dashboard.render.com** → serviço **studio-fd-demo** → **Environment**.
2. **Add Environment Variable** para cada uma: `DATABASE_URL`, `SUPABASE_URL`,
   `SUPABASE_SERVICE_KEY`, `ADMIN_EMAIL`, `ADMIN_SENHA_INICIAL`
   (a `SECRET_KEY` e a `SUPABASE_BUCKET` o Render já cria sozinho pelo `render.yaml`).
3. **Save Changes** → o Render reinicia o serviço (uns 3 a 5 minutos).
4. Abra o site: a faixa "Demonstração" some e aparece a tela de **entrada**.

## 7. Primeiro acesso

1. Entre com `ADMIN_EMAIL` e `ADMIN_SENHA_INICIAL`.
2. **Mais → Minha conta → Trocar senha.** Troque logo, principalmente se a senha
   inicial já foi escrita em algum lugar.
3. **Mais → Usuários → Novo acesso:** crie um acesso para **Douglas** e outro para **Fran**,
   cada um com o próprio e-mail e uma senha inicial. Eles trocam depois em *Minha conta*.
4. Depois do primeiro acesso, pode **apagar** a `ADMIN_SENHA_INICIAL` do Render
   (ela só é usada quando o banco ainda não tem nenhum usuário).

## 8. Cuidados do plano grátis

- **Pausa:** o Supabase pausa o projeto depois de cerca de **1 semana sem uso**. Usando todo dia,
  não acontece. Se pausar: painel do Supabase → **Restore project**.
- **Backup:** o plano grátis não garante backup que você possa restaurar. Toda semana,
  no sistema: **Mais → Backup → Baixar backup agora** e guarde o arquivo fora
  (pen drive ou Google Drive). O arquivo leva todos os dados e PDFs, sem as senhas.
- **Limites** (confira no site, mudam com o tempo): ~500 MB de banco e ~1 GB de arquivos —
  sobra para centenas de alunos.
- **LGPD:** anamnese é dado de saúde. Só crie acesso para quem precisa, não compartilhe
  senhas, e bloqueie o acesso de quem sair da equipe (**Mais → Usuários → Bloquear**).

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| Site não abre depois de colocar as chaves | Render → **Logs**. Mande a mensagem de erro (sem as chaves). |
| "password authentication failed" no log | A senha do banco no `DATABASE_URL` está errada, ou faltou trocar `[YOUR-PASSWORD]`. |
| "Network is unreachable" no log | Você usou a conexão **Direct**. Troque pela **Session pooler**. |
| Não consigo entrar | Confira `ADMIN_EMAIL`/`ADMIN_SENHA_INICIAL` no Render. Se já existir usuário, elas são ignoradas. |
| PDF não anexa | Confira se o bucket se chama `documentos` e se `SUPABASE_SERVICE_KEY` é a chave **secreta**. |
