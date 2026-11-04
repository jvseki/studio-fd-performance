# Etapa 1: arquitetura e roteiro de estudo

## Decisões e limites

O Studio atende com dois personais e precisa de operação local. Usamos um único
processo desktop, sem API ou servidor. A interface usa Qt Widgets; SQLAlchemy
traduz operações Python para SQLite; Alembic registra a evolução das tabelas.
O pacote PySide6 pode instalar componentes adicionais do Qt, mas o aplicativo
importa somente QtCore, QtGui e QtWidgets, sem usar WebEngine.

Esta etapa entrega a fundação. Ainda não modelamos agenda, mensalidades, caixa e
contratos para evitar antecipar regras enquanto o usuário estuda o projeto.
Os primeiros modelos já permitem relacionar alunos a planos. Nascimento, CPF,
endereço e dados de contratação podem estar ausentes durante o cadastro inicial.
Horários habituais e personal responsável terão relações próprias na etapa de
agenda; não serão guardados como texto sem estrutura na ficha.

## Caminho dos dados

```text
main.py → app.py → pastas → engine SQLite → migrações
                → fábrica de sessões → DashboardService → MainWindow

DashboardView → DashboardService → StudentRepository → Session → SQLite
             ← DashboardSummary ← contagem de alunos ativos
```

Uma `Session` representa uma unidade de trabalho com o banco. O serviço abre uma
sessão curta e a fecha ao terminar. A tela recebe um resumo simples, não uma
conexão aberta nem objetos ORM ligados à interface. Isso facilitará testar regras
e reutilizar serviços nas próximas telas.

## Mapa dos arquivos

| Arquivo ou pasta | Para que existe e como participa |
| --- | --- |
| `main.py` | Entrada mínima: chama `run()`; evita concentrar regras na inicialização. |
| `studio_fd/__init__.py` | Declara a versão inicial `0.1.0`. |
| `studio_fd/app.py` | Monta o QApplication, caminhos, logs, banco, serviço e janela; encerra o engine ao sair. |
| `utils/paths.py` | Separa recursos somente de leitura dos dados permanentes; permite diretório de teste explícito. |
| `database/base.py` | Base declarativa dos modelos e convenção de nomes das restrições do banco. |
| `database/session.py` | Cria engine e sessões; habilita chaves estrangeiras no SQLite e espera limitada por bloqueio. |
| `database/migrations.py` | Entrega uma conexão ao Alembic e aplica revisões pendentes. |
| `migrations/env.py` | Liga a execução do Alembic ao metadata e à conexão fornecida pela aplicação. |
| `migrations/versions/0001_initial.py` | Histórico explícito da criação de planos e alunos, independente da evolução dos modelos. |
| `models/plan.py` | Define nome, treinos semanais, preço, duração em meses, descrição e status do plano. |
| `models/student.py` | Define ficha básica, plano contratado, mensalidade própria, início e dia de vencimento. |
| `models/__init__.py` | Importa os modelos para registrar todas as tabelas no metadata. |
| `repositories/student_repository.py` | Centraliza a consulta de alunos ativos, sem dependência da interface. |
| `services/dashboard_service.py` | Abre a sessão, consulta o repositório e retorna um `DashboardSummary`. |
| `views/main_window.py` | Monta menu, logo, páginas e barra de status; navega e atualiza o Dashboard. |
| `views/dashboard.py` | Organiza indicadores e agenda inicial; consulta somente o serviço. |
| `views/placeholder.py` | Explica o escopo dos módulos futuros sem oferecer operações inexistentes. |
| `views/theme.py` | Centraliza cores, tipografia, espaçamento e estados visuais em QSS. |
| `widgets/metric_card.py` | Card reutilizável para um indicador, valor e descrição. |
| Demais `__init__.py` | Marcam os diretórios como pacotes Python e documentam sua responsabilidade. |
| `assets/README.md` | Explica onde colocar a logo original. |
| `requirements.txt` / `requirements-lock.txt` | Dependências diretas e registro completo do ambiente instalado. |
| `tests/test_database.py` | Verifica persistência, schema, relações, restrições e rejeição de revisão desconhecida. |
| `tests/test_interface.py` | Verifica navegação, atualização real do indicador, logo e largura mínima. |
| `tools/preview.py` | Renderiza uma captura usando dados temporários para inspeção visual. |
| `.gitignore` | Evita versionar ambiente, dados pessoais, bancos e arquivos gerados. |

Os caminhos abreviados na tabela estão dentro de `studio_fd/`, exceto os que
explicitamente começam por `migrations`, `assets`, `tests`, `tools` ou `requirements`.

## Dinheiro, datas e integridade

Valores monetários são inteiros em centavos: R$ 450,00 corresponde a `45000`.
Isso evita os erros de ponto flutuante. A mensalidade do aluno é independente do
preço atual do plano, preservando o valor contratado quando o plano mudar.
Datas usam `date`, sem horário. O Dashboard segue a data local do computador.

O banco rejeita nomes vazios, valores negativos, dias de vencimento fora de 1–31,
planos inexistentes e exclusão de planos ainda referenciados. CPF é único quando
preenchido; na próxima etapa o formulário deverá normalizar CPF e salvar ausência
como `None`, validar telefone e datas e tratar mensagens de erro em português.
Os dias 29–31 serão ajustados para o último dia do mês ao gerar mensalidades na
etapa financeira, sem mudar o dia contratado.

## Evolução do banco

Não usamos `drop_all()` nem `create_all()` como mecanismo de atualização.
Na abertura, o Alembic consulta `alembic_version` e executa somente revisões novas.
Reabrir o programa não apaga nem repovoa o banco. Uma revisão desconhecida gera
erro e impede a inicialização em vez de tentar converter dados silenciosamente.

Para uma mudança futura: alterar o modelo, criar um novo arquivo numerado em
`migrations/versions/`, definir `revision` e `down_revision`, escrever `upgrade()`
e verificar a atualização sobre uma cópia de dados anteriores. Mudanças de tabela
no SQLite podem usar `op.batch_alter_table`. A revisão `0001` é um registro
histórico e não deve acompanhar alterações futuras do modelo. Downgrade destrutivo
está bloqueado. Antes da primeira migração de um banco em uso, implementar snapshot
consistente com `sqlite3.Connection.backup()`; a etapa atual só cria o schema inicial.

## Próximas etapas propostas

1. **Alunos:** formulário, edição, pesquisa parcial sem diferença de acentos/caixa,
   gaveta A–Z e ficha. Não excluir histórico ao inativar um aluno.
2. **Planos:** cadastro e edição de valores pelos proprietários.
3. **Agenda:** definir expediente, duração e personais; agenda diária e recorrência.
   Usar slots explícitos, posições 1 e 2, restrição de posição e unicidade por
   data/slot/posição; validar também aluno duplicado e conflito de personal em
   transação. Recusar o terceiro aluno com a mensagem solicitada. Se sessões tiverem
   durações variáveis, validar sobreposição de intervalos, não somente início igual.
4. **Financeiro e caixa:** mensalidades por competência, vencimento, pagamento e
   forma; atraso calculado pela data. Integrar recebimento e entrada no caixa em
   uma transação, evitando contabilizar o mesmo pagamento duas vezes.
5. **Contratos:** copiar PDF para `data/contratos/`; persistir caminho relativo e
   metadados. Caminhos relativos permitem restaurar em outro computador.
6. **Backup:** arquivo único com manifesto, identificação do produto, versão do
   schema/aplicativo, SQLite consistente, contratos e configurações. Não incluir
   a própria pasta de backups. Validar integridade, caminhos do ZIP, tamanhos e
   compatibilidade em diretório separado; bloquear escrita durante restauração,
   criar backup anterior e substituir com recuperação em caso de falha. Adicionar
   backups locais automáticos e política de retenção visível ao usuário.
7. **Relatórios, configurações e distribuição final:** validar os fluxos anteriores
   antes da versão de uso operacional. A pedido do usuário, foi antecipado um
   instalador experimental da etapa 1; veja `DISTRIBUICAO.md`. Ele inclui assets e
   migrations como recursos e mantém os dados separados da instalação.

O diretório permanente protege contra substituição do executável, mas não é uma
cópia de segurança. Nesta primeira etapa os botões e rotinas de backup ainda não
existem; a interface informa isso na página correspondente.
