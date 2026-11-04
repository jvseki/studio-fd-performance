# Studio FD Performance — etapa 2 + atualizações · versão 0.2.1

Aplicativo **desktop nativo para Windows**, escrito em Python com PySide6,
SQLAlchemy e SQLite. Os cadastros operam localmente, sem servidor ou internet.
O contato opcional pelo WhatsApp abre um link externo e precisa de internet.
A instalação inicial das dependências de desenvolvimento precisa de internet.

## Executar

Na Área de Trabalho, dê dois cliques em **Studio FD Performance - Desenvolvimento**.
Esse atalho abre o projeto e acompanha as alterações feitas no código.
Leia também [o guia de uso e instalação](docs/COMO_USAR.md).
Para colaborar e entender o que deve ficar fora do GitHub, leia
[as orientações do repositório público](docs/REPOSITORIO_PUBLICO.md).

Para abrir pelo terminal:

No PowerShell, na pasta `C:\Studio performance`:

```powershell
.\.venv\Scripts\python.exe main.py
```

O ambiente `.venv` foi preparado com Python 3.13. Para preparar em outro computador:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Não é necessário ativar o ambiente nem mudar a política de execução do PowerShell.
`requirements.txt` fixa as três dependências diretas; `requirements-lock.txt`
registra também as versões transitivas verificadas neste Windows. Para reproduzir
exatamente esse ambiente, instale usando o arquivo de lock.

## O que está pronto

- Janela nativa com identidade preto/grafite/dourado, menu lateral e navegação.
- Dashboard inicial com contagem real de alunos ativos e atualização manual.
- Cadastro, edição, ficha e inativação de alunos.
- Pesquisa por nome sem diferença de acentos, gaveta alfabética e filtro de status.
- Cadastro e edição de planos, com mensalidade individual preservada.
- Mensagem editável e botão para abrir conversa no WhatsApp, com envio manual.
- Modelos `Student` e `Plan`, SQLite local e primeira migração Alembic.
- Diretórios persistentes separados do código e dos recursos do programa.
- Tratamento de falha na inicialização e registro de diagnóstico em arquivo local.
- Testes de persistência, restrições, migração e interface.

O banco começa vazio, sem alunos fictícios nem preços de planos predefinidos.
Os indicadores que dependem de módulos futuros exibem `—`. Não há como calcular
horários disponíveis antes de definir expediente e duração das sessões.

As telas de Agenda, Financeiro, Caixa, Contratos, Relatórios, Backup e Configurações
ainda são reservas de navegação. **Agendamento, geração de mensalidades, registro
de pagamentos e backup/restauração ainda não estão implementados.**
O instalador desta entrega fica em `release/StudioFDPerformance-Setup-0.2.1.exe`.
Há cópia automática antes de abrir uma nova versão sobre dados existentes;
a tela de exportação/restauração e backups periódicos continuam pendentes.
O de versão 0.1.0 permanece uma cópia histórica da primeira etapa.

## Logo

Salve a logo original em **`assets/logo.png`** e reinicie o aplicativo. A interface
mantém a proporção da imagem. Enquanto o arquivo não existir, exibe uma assinatura
tipográfica provisória; não é uma reprodução da logo enviada no chat.

## Onde ficam os dados

O caminho padrão independe da pasta em que o aplicativo foi instalado:

```text
%LOCALAPPDATA%/StudioFDPerformance/data/
├── studio_fd.db
├── contratos/
├── backups/
├── configuracoes/
└── logs/studio_fd.log
```

O banco é criado na primeira inicialização. A revisão atual fica na tabela
`alembic_version`. A pasta de recursos do PyInstaller contém somente
recursos, nunca esses dados. Cada conta Windows tem sua própria pasta de dados.
Os diretórios de contratos, backups e configurações estão preparados. A cópia
antes de uma atualização já usa essas pastas; suas telas completas serão
desenvolvidas nas etapas correspondentes.

Para testar com dados separados, defina um caminho absoluto antes de executar:

```powershell
$env:STUDIO_FD_DATA_DIR = 'C:\Studio performance\data'
.\.venv\Scripts\python.exe main.py
```

Essa variável vale para a sessão atual do terminal. Para voltar ao local padrão:

```powershell
Remove-Item Env:STUDIO_FD_DATA_DIR
```

## Estudar a arquitetura

Leia [o guia de arquitetura e arquivos](docs/ARQUITETURA.md). Todos os arquivos de
código no projeto estão completos, sem trechos omitidos ou pseudocódigo.
As mudanças desta entrega estão explicadas em [Etapa 2](docs/ETAPA_2.md).
O fluxo de atualização está em [Atualizações](docs/ATUALIZACOES.md), e os testes
desta entrega estão registrados em [Validação 0.2.1](docs/VALIDACAO_0.2.1.md).

## Gerar uma atualização

Dê dois cliques em **Gerar atualizacao.cmd** ou pressione **Ctrl+Shift+B** no
VS Code. Aceite a próxima versão, descreva a mudança e aguarde **PRONTO!**.
Leve o novo instalador da pasta `release` para a academia e execute com o Studio
fechado, na mesma conta Windows. Consulte [o guia de atualizações](docs/ATUALIZACOES.md).

O executável usa PyInstaller em modo pasta, sem UPX; o Inno Setup reúne essa pasta
em um único instalador. O aplicativo instalado inclui o Python e suas bibliotecas.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\tools\build_windows.ps1 -InnoCompiler 'C:\Studio performance\build\toolchain\inno\ISCC.exe'
```

`requirements-build-lock.txt` registra o ambiente de empacotamento completo.
O script gera ícone, executa testes, empacota e compila o instalador com hash SHA-256.
Não inclui bancos, contratos, logs ou dados do Studio. O instalador não tem
assinatura digital comercial; o hash verifica integridade, não certifica segurança.
Antes de distribuir uma nova compilação, siga [as verificações de distribuição](docs/DISTRIBUICAO.md).

## Verificar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tools\preview.py
```

Os testes usam bancos temporários e a interface fora da tela; não inserem dados
no banco do Studio. As prévias atuais são salvas em `docs/*-etapa-2.png`.

Documentação oficial usada como referência: [Qt for Python](https://doc.qt.io/qtforpython-6/gettingstarted.html),
[SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/intro.html) e
[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
