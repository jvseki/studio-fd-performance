# Validação do instalador 0.1.0

Verificado em 03/11/2026, Windows 11 x64, versão 10.0.26200.

Artefato: `release/StudioFDPerformance-Setup-0.1.0.exe`

- Tamanho: 40.174.855 bytes (aproximadamente 40,2 MB).
- SHA-256: `594D99C89AF548F40B206E4C97918926DD9B6ACAC2D4EFC44DFB2B0F920A5132`.
- Assinatura Authenticode: `NotSigned` (o instalador do Studio não está assinado).
- Dependências: `pip check` sem incompatibilidades.
- Testes de banco e interface: 6 aprovados.
- Executável empacotado: abertura e fechamento normal duas vezes, revisão `0001`,
  integridade SQLite e registro de teste preservado em dados temporários.
- Instalador: instalação silenciosa em destino isolado dentro de `build`, abertura
  do executável instalado, desinstalação e remoção do registro de instalação aprovadas.
- Banco real: hash idêntico antes e depois do teste de instalação/desinstalação;
  leitura com compartilhamento, sem fechar a aplicação do usuário.
- Conteúdo: 219 arquivos no pacote, nenhum arquivo `.db`, `.db-wal` ou `.db-shm`.
- Microsoft Defender: verificação personalizada da pasta `release` concluída com
  código 0 e mensagem `found no threats`. Assinaturas: `1.463.108.0`.
- Atalho de desenvolvimento: destino `pythonw.exe`, argumento `main.py`, diretório
  de trabalho do projeto e ícone FD conferidos na Área de Trabalho do OneDrive.

O teste foi feito neste computador, não em uma máquina Windows limpa ou em todas
as versões suportadas. Uma verificação sem detecções não certifica ausência de
malware nem impede alertas futuros de reputação. Não houve alteração das proteções
do Windows. Os limites funcionais da etapa 1 continuam descritos em `COMO_USAR.md`.

O instalador é uma cópia da versão atual. Mudanças posteriores no projeto exigem
gerar e testar uma nova compilação; o atalho de desenvolvimento lê o código atual.
