# Empacotamento e atualizações Windows

Para o uso diário, siga [o guia de atualizações](ATUALIZACOES.md).

## Arquivos novos e comunicação entre eles

- `tools/create_icon.py` desenha o monograma tipográfico FD e grava `assets/app.ico`
  com vários tamanhos. O ícone é usado pela janela, pelo atalho e pelo instalador.
  Não tenta reproduzir a logo original.
- `tools/create_shortcut.ps1` localiza a Área de Trabalho da conta Windows, inclusive
  quando ela está no OneDrive, e cria um `.lnk` para `pythonw.exe main.py`.
  Não muda a política de execução do PowerShell.
- `packaging/studio_fd.spec` define o conteúdo do executável PyInstaller: código,
  Python, bibliotecas, assets, migrações, ajuda e licenças. Não inclui dados pessoais.
  O modo pasta mantém as DLLs separadas e evita extração do programa a cada abertura.
- `tools/release.py` lê e atualiza a versão em `studio_fd/__init__.py`, gera
  `build/windows_version_info.txt` e `build/release_version.iss` para manter a
  versão do programa e do instalador consistente. São metadados, não assinatura.
- `packaging/studio_fd.iss` define instalação por usuário, atalhos, português e
  desinstalação. O identificador AppId deve permanecer estável nas atualizações.
- `packaging/LEIA_ANTES.txt` informa no assistente os limites da versão inicial.
- `packaging/THIRD_PARTY_NOTICES.txt` acompanha as licenças das bibliotecas.
- `Gerar atualizacao.cmd` e a tarefa do VS Code chamam `tools/release.py`.
  `tools/build_windows.ps1` também encaminha para esse gerador.
- `tools/test_upgrade.py` testa instalação da versão anterior, atualização,
  reinstalação e desinstalação em uma pasta isolada, preservando cadastros e backups.
- `tools/test_frozen.py` abre o `.exe` real com dados temporários, fecha pela mensagem
  normal do Windows, reabre e verifica schema, integridade e persistência.
- `tools/test_installer.ps1` instala em uma pasta de teste dentro de `build`, verifica
  o executável instalado, desinstala e compara o hash do banco real antes e depois.
  Recusa o teste se já houver uma versão instalada para esse usuário.
- `requirements-build.txt` e `requirements-build-lock.txt` separam as ferramentas de
  empacotamento das dependências usadas no desenvolvimento normal.

`views/main_window.py` recebeu apenas a definição do ícone da janela. O carregamento
da logo original continua tendo preferência, quando o arquivo estiver disponível.

## Verificação de uma compilação

```powershell
.\.venv\Scripts\python.exe tools\test_frozen.py '.\dist\Studio FD Performance\Studio FD Performance.exe'
```

Depois, teste o instalador em uma pasta isolada, sem atalhos, execute o mesmo teste
contra o `.exe` instalado e teste a desinstalação. Não use a pasta do programa de
um cliente como destino de teste. Não execute dois instaladores simultaneamente.
Registre resultado, versão do Windows, tamanho, assinatura e SHA-256 na entrega.

O diretório de instalação padrão é
`%LOCALAPPDATA%\Programs\Studio FD Performance`.
O banco permanece em `%LOCALAPPDATA%\StudioFDPerformance\data`; o instalador não
contém instrução para remover essa pasta. O logotipo de `assets` é copiado para
os recursos do pacote durante o build; adicioná-lo ao projeto após gerar o `.exe`
não atualiza um instalador já pronto.

## Segurança e limites

Usar fontes oficiais, incluir somente os arquivos necessários, examinar os artefatos
com o antivírus e testar instalação/abertura ajuda a reduzir problemas, mas não
garante compatibilidade com todos os computadores nem ausência de detecções futuras.
Não criar exclusões no antivírus, não desligar SmartScreen e não usar certificados
autoassinados como se fossem certificados reconhecidos por terceiros.

O Inno Setup usado para o build é obtido no site oficial e a assinatura de seu
instalador é verificada antes da preparação. Isso não assina automaticamente o
instalador do Studio. Distribuição pública posterior deve considerar assinatura
de código adequada e testes em Windows limpo; a versão atual é de desenvolvimento.

Fontes: [PyInstaller](https://pyinstaller.org/en/stable/usage.html),
[Inno Setup](https://jrsoftware.org/isinfo.php) e
[Microsoft SmartScreen](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/).
