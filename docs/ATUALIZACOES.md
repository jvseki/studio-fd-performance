# Como gerar e instalar uma atualização

## No seu computador de desenvolvimento

1. Faça as alterações e **salve todos os arquivos no VS Code**.
2. Dê dois cliques em **Gerar atualizacao.cmd**, na pasta do projeto.
   Outra opção: no VS Code, pressione **Ctrl+Shift+B** e escolha
   **Studio FD: Gerar atualização**, caso apareça uma lista.
3. O programa mostra a versão atual e sugere a próxima: por exemplo,
   de `0.2.1` para `0.2.2`. Pressione Enter para aceitar ou digite outra maior.
4. Escreva uma frase com o que mudou, como “Correção na pesquisa de alunos”.
5. Aguarde aparecer **PRONTO!**. Durante a geração, não altere os arquivos do projeto.
6. Abra a pasta **release** e pegue o instalador com o número informado.

O processo confere dependências, executa os testes, prepara o ícone, monta o
programa, abre e fecha o executável com dados fictícios e cria o instalador.
Leva alguns minutos. Se algum passo falhar, ele informa o erro e não libera
um novo instalador na pasta release. Versões anteriores são preservadas.

Junto do `.exe`, ficam um `.LEIA-ME.txt` com as instruções e o resumo das mudanças,
um `.sha256` para conferência de integridade e um `.json` com os dados da entrega.
Você leva **somente o instalador e, se quiser, as instruções** para a academia.
Não leve `.venv`, o projeto completo nem seu banco de testes.

Salvar código ou atualizar o próprio VS Code **não gera uma entrega**. A geração
começa quando você executa o arquivo ou a tarefa. Isso permite terminar e conferir
uma alteração antes de disponibilizá-la.

## No computador da academia — presencialmente ou pelo AnyDesk

1. Use a **mesma conta do Windows** em que o Studio costuma funcionar.
2. Feche todas as janelas do Studio, inclusive alguma versão de desenvolvimento.
3. Copie o novo instalador para o computador. Pelo AnyDesk, use a transferência
   de arquivos disponível na sua sessão ou outro meio já utilizado por vocês.
4. Execute o instalador e mantenha a pasta sugerida. **Não precisa desinstalar antes.**
5. Abra pelo atalho **Studio FD Performance**.
6. Confira o número da versão no rodapé do menu lateral, os alunos, os planos
   e a abertura de uma ficha.

A atualização troca os arquivos do programa. Os dados ficam separados em:

```text
%LOCALAPPDATA%\StudioFDPerformance\data
```

Copie esse caminho para a barra do Explorador de Arquivos para abrir a pasta.
Se outra conta Windows for usada, haverá outra pasta de dados: os cadastros
da conta original não aparecem automaticamente nela.

## Cópia antes da atualização

A partir da versão 0.2.1, na primeira abertura de uma versão nova com banco já
existente, o Studio faz uma cópia **antes de preparar/migrar o banco**. O arquivo
fica em `data\backups\StudioFD_Antes_VERSAO_DATA_IDENTIFICADOR.zip` e contém:

- Um retrato consistente do banco SQLite.
- Arquivos das pastas `contratos` e `configuracoes`.
- Um manifesto com versões, revisão do banco e hashes dos arquivos.

Se a cópia falhar, o aplicativo interrompe a abertura e mostra um aviso. A versão
dos dados só é confirmada depois da inicialização bem-sucedida. Reabrir ou reinstalar
a mesma versão não cria outra cópia. Uma instalação sem dados prévios não precisa
de cópia. Logs e backups anteriores não entram no ZIP.

Essa proteção é local: **não substitui cópias periódicas em outro dispositivo**.
A tela de exportação/restauração ainda será desenvolvida; a recuperação é técnica,
com o aplicativo fechado e análise da versão e do manifesto. Não extraia um ZIP
por cima dos dados em uso. O teste automatizado confere que o banco copiado pode
ser aberto e que os registros e arquivos continuam presentes.

Não use um instalador antigo para tentar desfazer uma atualização. O aplicativo
novo recusa dados marcados por uma versão posterior e o instalador novo detecta
executável posterior no destino. Os instaladores 0.1.0 e 0.2.0, guardados como
histórico, foram criados antes dessas proteções. Voltar de versão exige avaliar
também as migrações e os dados; ainda não há retorno automático.

## Se der problema

- **Falha ao gerar:** leia a última mensagem do terminal. Nenhum arquivo novo deve
  ser entregue sem a mensagem PRONTO. As pastas `build/release-stage-*` guardam
  os arquivos intermediários; não distribua os instaladores dessas pastas.
- **Falha ao abrir após atualizar:** guarde o texto do aviso e o log
  `data\logs\studio_fd.log`. Não apague o banco ou a pasta de backups.
- **Aviso do antivírus:** não desative a proteção. O instalador ainda não tem
  assinatura comercial; alertas precisam ser avaliados pelo texto exato.

## Para manutenção do projeto

A versão do código fica em `studio_fd/__init__.py`. O gerador atualiza esse único
lugar e produz os metadados do executável e do instalador em `build`. Não é preciso
editar a versão manualmente em três arquivos. Duas gerações simultâneas são recusadas.
O AppId do instalador permanece o mesmo para que as versões atualizem a instalação.

Pré-requisitos nesta máquina: `.venv` com `requirements-build-lock.txt` instalado
e Inno Setup em `build/toolchain/inno/ISCC.exe`. Para outro caminho, use:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\release.py --interactive --inno-compiler 'C:\caminho\ISCC.exe'
```

Modo sem perguntas, informando uma versão maior que a atual:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\release.py --version 0.2.2 --notes 'Resumo da melhoria'
```

Antes de entregar, teste a instalação e atualização em uma conta sem Studio instalado:

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\test_upgrade.py --previous 0.2.0
```

Esse teste instala e remove apenas uma cópia isolada em `build`, recusa execução
se já existir Studio registrado na conta e verifica que o banco real não mudou.
Não execute dois testes de instalador simultaneamente.

Referências técnicas: [identificador de atualização do Inno Setup](https://jrsoftware.org/ishelp/topic_setup_appid.htm)
e [controle de acesso simultâneo do Qt](https://doc.qt.io/qt-6/qlockfile.html).
