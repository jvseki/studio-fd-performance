# Como usar o Studio FD Performance — versão 0.2.1

## Abrir no computador de desenvolvimento

Dê dois cliques em **Studio FD Performance - Desenvolvimento**, na Área de
Trabalho. Ele abre o projeto diretamente, sem janela de terminal. Esse atalho
acompanha as próximas alterações no código. Não mova a pasta
`C:\Studio performance` nem apague `.venv`, pois o atalho depende delas.
Se estiver aberto durante uma atualização, feche e abra novamente.

## Cadastrar um aluno

1. Clique em **Alunos → + Novo aluno**.
2. Digite **nome** e **telefone com DDD**.
3. Clique em **Salvar aluno**. A ficha abre após o cadastro.

Isso basta para começar. Plano, mensalidade, vencimento e início são opcionais.
**Mostrar dados opcionais** revela nascimento, CPF, endereço e observações.
Se um campo estiver inválido, o formulário explica e mantém o que foi digitado.

## Criar planos

Em **Planos → + Novo plano**, informe nome, treinos por semana, mensalidade e
duração. Também é possível criar um plano no formulário do aluno. Ao selecionar
um plano, o sistema sugere o preço; você pode ajustar o valor combinado com o aluno.
Alterar o preço do plano depois não altera as mensalidades já contratadas.

Clique no plano para editar. Desmarcar **Plano ativo** impede novas vinculações
e preserva os alunos que já estavam vinculados.

## Encontrar e editar

Em **Alunos**, digite parte do nome ou clique em uma letra. A pesquisa encontra
`João` mesmo se você digitar `joao`. Nome, letra e status podem ser combinados;
**Limpar filtros** volta a mostrar todos os alunos.

Clique no aluno para abrir a ficha. Use **Editar aluno** para mudar os dados.
Para inativar, desmarque **Aluno ativo** e salve. O cadastro permanece guardado.
O Dashboard conta somente os alunos ativos.

## Falar pelo WhatsApp

1. Abra a ficha do aluno e clique em **WhatsApp**.
2. Revise ou escreva a mensagem.
3. Clique em **Abrir conversa no WhatsApp**.
4. Confira o destinatário e envie pelo próprio WhatsApp.

O telefone é brasileiro, com DDD; o sistema acrescenta o código `55` sem duplicá-lo.
O link pode abrir o navegador ou encaminhar para o aplicativo, dependendo do
computador. É preciso internet e uma conta do WhatsApp conectada. O Studio não
verifica se o número tem WhatsApp, não confirma entrega e não envia automaticamente.
Os cadastros continuam funcionando offline.

## Como serão as cobranças

Nesta versão, valor e dia de vencimento são informações da ficha. **Ainda não há
geração de mensalidades, cobrança automática, Pix integrado ou boleto.**

O fluxo proposto é: gerar mensalidade por aluno/mês, acompanhar vencimento,
preparar um lembrete para revisão no WhatsApp e registrar data/forma de pagamento
quando o Studio confirmar o recebimento. Enviar mensagem não significa pagamento.

Os traços `—` significam que o indicador depende de um módulo futuro; não são erro.
Agenda, financeiro, caixa, contratos, relatórios e a tela de exportação/restauração
ainda serão construídos. Existe uma cópia automática antes de abrir uma nova
versão com dados existentes; backups periódicos ainda não estão ativos.

## Instalar a versão empacotada

1. Abra `StudioFDPerformance-Setup-0.2.1.exe`, dentro da pasta `release` do projeto.
2. Leia o aviso sobre a etapa atual e prossiga no assistente.
3. Mantenha marcada a opção de criar atalho na Área de Trabalho.
4. Conclua e abra **Studio FD Performance**.

O instalador contém o programa e suas dependências. No computador de destino não
é necessário instalar Python. Os cadastros funcionam sem internet; o WhatsApp precisa de conexão.
O alvo é Windows 10/11 de 64 bits; outras configurações não foram validadas.

O atalho **sem “Desenvolvimento”** abre a versão instalada. Ela só recebe mudanças
quando um novo instalador é gerado e aplicado. Os dois atalhos usam os mesmos
dados na mesma conta Windows, salvo configuração explícita de outra pasta.

Para gerar a próxima versão e instalá-la presencialmente ou pelo AnyDesk,
siga [o guia de atualizações](ATUALIZACOES.md). O arquivo **Gerar atualizacao.cmd**
na pasta do projeto conduz a geração. Não é preciso desinstalar a versão anterior.

## Dados e logo

Os dados ficam em `%LOCALAPPDATA%\StudioFDPerformance\data`, separados do programa.
Desinstalar o aplicativo remove seus arquivos e atalhos, mas preserva essa pasta.
Não há dados pessoais dentro do instalador.
A etapa 2 utiliza as tabelas existentes, sem recriar o banco.

No projeto, coloque a imagem original em `assets/logo.png` e reinicie para carregar
a logo. Para incluí-la na versão instalada, gere o instalador novamente.
O ícone FD atual é uma identificação tipográfica provisória.

## Sobre avisos do Windows

O instalador inicial ainda não tem assinatura digital reconhecida. Isso pode
produzir avisos de reputação do Windows; assinatura e reputação são diferentes de
uma verificação de malware. Não é possível garantir “zero alertas” ou “zero erros”
em todos os computadores. Não desative o antivírus para instalar.

Se aparecer uma detecção ou falha, guarde o texto exato do aviso para investigação.
O log do aplicativo está em
`%LOCALAPPDATA%\StudioFDPerformance\data\logs\studio_fd.log`.

Referência: [como o Microsoft Defender SmartScreen avalia aplicativos](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/).
Contato: [recurso oficial clique para conversa do WhatsApp](https://faq.whatsapp.com/5913398998672934/?locale=pt_BR).
