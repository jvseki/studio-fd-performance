# Etapa 2 — alunos, planos e WhatsApp

O objetivo é cadastrar com nome e telefone, encontrar a ficha rapidamente e
iniciar contato manual. Informações opcionais não bloqueiam um cadastro simples.

## Arquivos e comunicação

Os caminhos abaixo estão dentro de `studio_fd/`.

| Arquivo | Responsabilidade |
| --- | --- |
| `services/records.py` | Define entradas e resultados imutáveis compartilhados entre serviços e telas. |
| `services/student_service.py` | Valida e salva em transação; trata CPF repetido e planos inativos; retorna a ficha sem sessão aberta. |
| `services/plan_service.py` | Valida e salva planos com os valores escolhidos pelo Studio. |
| `services/whatsapp_service.py` | Prepara saudação e URL; não faz rede nem envia mensagens. |
| `repositories/student_repository.py` | Pesquisa nome, letra e status; lê fichas e continua fornecendo a contagem do Dashboard. |
| `repositories/plan_repository.py` | Centraliza consultas de planos. |
| `utils/formatting.py` | Normaliza telefone, valida dígitos do CPF, remove acentos da pesquisa e formata valores. |
| `widgets/forms.py` | Reúne campos de dinheiro, data opcional e estrutura dos formulários. |
| `views/students.py` | Lista, filtros, gaveta alfabética e abertura da ficha. |
| `views/student_form.py` | Cadastro/edição e criação de plano sem sair do formulário. |
| `views/student_profile.py` | Apresenta ficha, edição e acesso ao WhatsApp. |
| `views/plans.py` | Lista e formulário dos planos. |
| `views/whatsapp.py` | Mostra destinatário e texto editável; abre o link após clique do usuário. |

`app.py` entrega os novos serviços a `main_window.py`, que substitui as páginas
de Alunos e Planos. Sinais Qt atualizam o Dashboard após salvar alunos. A navegação
também atualiza as listas. `dashboard.py` ganhou o botão Ver alunos. `theme.py`
estiliza os formulários; SVGs em `assets` deixam indicadores e setas legíveis.

## Banco e regras

O schema permanece em `0001`; os modelos iniciais já tinham esses campos. Não
houve migração nem exclusão/recriação de tabelas. `database/session.py` registra
uma função SQLite por conexão para comparar nomes sem acentos; os nomes originais
continuam preservados.

CPF vazio vira `NULL`, e CPF preenchido deve ter dígitos válidos e ser único. Isso
não consulta situação cadastral. Telefone aceita formato brasileiro com DDD ou
com `+55`. Dinheiro é guardado em centavos. A mensalidade individual não acompanha
mudanças posteriores de preço do plano. Novos vínculos exigem plano ativo; os
vínculos existentes continuam editáveis quando o plano é inativado.

Cancelar um formulário não salva o aluno. Um plano criado e salvo dentro desse
formulário é um cadastro independente e permanece mesmo se o aluno for cancelado.

## WhatsApp e cobrança

O botão usa o [clique para conversa oficial](https://faq.whatsapp.com/5913398998672934/?locale=pt_BR).
O serviço gera URL com `55` + DDD + número e codifica acentos, símbolos e quebras de
linha. A tela chama `QDesktopServices` após revisão. Não há automação de envio,
confirmação de entrega ou registro financeiro associado ao clique.

Para a etapa financeira: mensalidade única por aluno/competência, valor contratado,
vencimento e pagamento; atraso derivado da data. Ajustar dias 29–31 ao último dia
de meses menores. Lembretes deverão usar uma mensalidade específica e continuar
editáveis. Baixa só após confirmar recebimento. Pix integrado e boleto exigem uma
integração específica e não fazem parte desta entrega.

## Verificação e empacotamento

`tests/test_registration.py` cobre validações, pesquisa, transações, status, preço
contratado e URLs. `tests/test_registration_ui.py` cobre salvar/editar/cancelar,
filtros, ficha, Dashboard e abertura do WhatsApp com simulação. Nenhuma mensagem
foi enviada nos testes. `tools/preview.py` usa um banco temporário com demonstrações.

O instalador passou para `0.2.0`; o antigo não foi sobrescrito. Os scripts de build
e teste leem a versão do pacote para escolher o arquivo correspondente. O banco
permanece fora do executável e do instalador. Todos os arquivos estão completos
no projeto, sem pseudocódigo ou trechos omitidos.
