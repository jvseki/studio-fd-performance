# Validação da versão 0.2.0

Data: 03/11/2026. Ambiente: Windows 11 x64, Python 3.13 e PySide6 6.12.

- 16 testes aprovados: schema, persistência, integridade, relações, validações,
  CPF repetido, pesquisa sem acentos, inativação, mensalidade individual,
  cadastro/edição/cancelamento pelos formulários, filtros e Dashboard.
- WhatsApp: telefone e URL conferidos, texto com acentos/símbolos preservado,
  abertura somente após clique e tratamento de falha. A chamada externa foi
  simulada nos testes; nenhuma mensagem foi enviada.
- Interface: capturas inspecionadas de lista, cadastro e ficha. Campos opcionais
  recolhidos, indicadores legíveis e formulários ajustados à altura disponível.
- Instalador: instalação em pasta isolada, duas aberturas do executável instalado,
  fechamento normal, preservação do registro de teste e desinstalação aprovados.
- Banco real: hash idêntico antes/depois do teste de instalação/desinstalação.
  Nenhum banco pessoal foi incluído no pacote. O schema continua na revisão 0001.
- Dependências: `pip check` sem incompatibilidades.
- Microsoft Defender: verificação do arquivo 0.2.0 com código 0 e `found no threats`.

Artefato: `release/StudioFDPerformance-Setup-0.2.0.exe`.
Tamanho: 40.207.964 bytes.
SHA-256: `A171805E19A054AE3DB49AB1A8E1F9F5E29C4C677BAFA5132305F77BB480050C`.

O teste foi realizado neste computador. O instalador continua sem assinatura
digital comercial. A varredura não garante ausência de alertas futuros em outros
ambientes. Não houve alteração das proteções do Windows.

Financeiro, agenda e backup ainda não foram implementados. Mensalidade e vencimento
na ficha são informações cadastrais; não geram cobrança ou baixa de pagamento.
