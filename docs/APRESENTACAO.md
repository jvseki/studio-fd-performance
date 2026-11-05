# Apresentação curta do Studio FD Performance

Objetivo: mostrar um protótipo funcional de cadastro e atendimento e colher
opiniões antes de investir nas demais funções. Não apresentar como sistema completo.

## Roteiro de aproximadamente cinco minutos

1. **Dashboard:** mostre o visual do Studio e a contagem de alunos ativos.
   Indicadores com traços dependem de módulos futuros.
2. **Planos:** crie um plano de demonstração com nome, frequência e valor.
3. **Alunos:** cadastre um aluno fictício, selecione o plano e mostre que o valor
   individual pode ser ajustado. Nome e telefone são os campos básicos.
4. **Pesquisa e ficha:** procure o aluno, abra a ficha e edite uma informação.
5. **WhatsApp:** mostre a revisão da mensagem. Para abrir e enviar de verdade,
   use somente um número seu ou autorizado. Não envie para telefones de exemplo.
6. **Fechamento:** explique que os cadastros ficam no computador e que há instalador
   e um procedimento de atualização que preserva os dados.

## Ambiente separado para a demonstração

Feche a janela de desenvolvimento e abra um terminal PowerShell na pasta do projeto:

```powershell
$env:STUDIO_FD_DATA_DIR = Join-Path (Get-Location) '.test-data\apresentacao'
.\.venv\Scripts\python.exe main.py
Remove-Item Env:STUDIO_FD_DATA_DIR
```

Os cadastros criados nessa janela ficam separados do banco normal. A última linha
retira a configuração do terminal após fechar o aplicativo. A pasta de demonstração
é ignorada pelo Git. O programa não vem com alunos de demonstração pré-cadastrados.

## O que explicar sobre as outras telas

Agenda, Financeiro, Caixa, Contratos, Relatórios e Configurações ainda são reservas
de navegação. A cópia antes de atualizar funciona, mas a tela de exportação e
restauração de backups não está pronta. Valor e vencimento na ficha não geram
mensalidades, cobranças ou baixas de pagamento.

## Próximo investimento pequeno, se houver interesse

Primeiro valide com o Studio se o cadastro é simples e se as informações atendem
à rotina. Se essa parte for aprovada, escolha uma única prioridade: por exemplo,
mensalidade com vencimento e botão para registrar pagamento manual. Agenda completa,
Pix/boleto, relatórios e automações podem ficar para etapas posteriores.

## Ícone da barra de tarefas

O código identifica o processo como `StudioFDPerformance.Desktop` antes de criar
a interface e define o ícone do aplicativo. Feche e reabra pelo atalho de
desenvolvimento para receber alterações do código. Um instalador já gerado só
recebe a correção quando uma nova versão for empacotada.

O ícone é o monograma FD provisório. A logo original ainda não está no arquivo
`assets/logo.png`. Se houver um atalho antigo do Python fixado na barra, desafixe
somente esse atalho e use o atalho do Studio.

Referência: [identificação do aplicativo na barra de tarefas do Windows](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid).
