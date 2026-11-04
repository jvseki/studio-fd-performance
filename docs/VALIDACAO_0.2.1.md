# Validação da versão 0.2.1

Data: 04/11/2026. Ambiente: Windows 11 x64 (build 26200), Python 3.13.15,
PySide6 6.12.0, PyInstaller 6.22.3 e Inno Setup 7.1.1.

- 24 testes aprovados, incluindo os 16 testes anteriores de banco, cadastro,
  pesquisa, planos, formulários e WhatsApp.
- Novos testes: cópia consistente do banco, leitura do banco recuperado, arquivos
  e hashes do ZIP, instalação nova, banco legado sem marcador de versão,
  reabertura sem duplicar cópia, recusa de versão anterior, marcador inválido,
  corrupção do banco e falha de gravação da cópia.
- Falha no backup interrompe a inicialização antes de abrir/migrar o banco e
  antes de confirmar a versão dos dados.
- Gerador: versões inválidas, antigas ou já entregues são recusadas; versão dos
  metadados consistente; falha de verificação restaura a versão do código e não
  publica instalador. O gerador real produziu esta entrega com sucesso.
- `pip check`: nenhuma dependência incompatível.
- Executável empacotado: duas aberturas e fechamentos normais; migração,
  integridade e persistência aprovadas com dados fictícios.
- Atualização real em pasta isolada: instalador 0.2.0, cadastro de plano/aluno,
  mensalidade negociada e contrato fictício; instalação 0.2.1 sobre a mesma pasta;
  primeira abertura, verificação do ZIP e comparação integral dos registros.
- Reabertura e reinstalação 0.2.1 preservaram os dados e não duplicaram o backup.
- Desinstalação removeu a cópia de teste e seu registro, preservando dados e backup.
- Hash do banco real idêntico antes/depois. Nenhum banco está no pacote distribuído.
- Versão nas propriedades do executável: arquivo `0.2.1.0`, produto `0.2.1`.
- Microsoft Defender: varredura do instalador com código 0 e `found no threats`.
  Nenhuma proteção foi desativada. Arquivo sem assinatura digital comercial.
- SHA-256 recalculado e comparado com o arquivo de checksum: idêntico.
- Tarefa do VS Code: JSON válido; usa o mesmo gerador executado nesta validação.

Instalador: `release/StudioFDPerformance-Setup-0.2.1.exe`.
Tamanho: **40.225.227 bytes**.
SHA-256: `4C0C06224D4E62DD8C05B4D4C27379FED4525D236B8A87FC903DBAA903AA60C2`.

Evidências locais do teste de atualização: `build/upgrade-check-d1ce2bd9/`,
incluindo logs dos instaladores, resultado, dados fictícios e backup verificado.
As versões 0.1.0 e 0.2.0 continuam guardadas na pasta release como histórico.

Limites: testes realizados neste computador; não garantem ausência de alertas
ou falhas em todo Windows. Não há atualizador por internet, restauração pela
interface ou retorno automático para versão anterior. A proteção contra versões
anteriores no aplicativo foi testada; a condição do instalador para bloquear um
executável futuro foi compilada, mas não simulada neste teste de atualização.
Não houve envio de mensagens pelo WhatsApp ou implantação no computador da academia.
