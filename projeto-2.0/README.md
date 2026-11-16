# Studio FD Performance — versão web

Protótipo local em React, TypeScript e Vite para a gestão do Studio pelos donos.
O aluno acessa somente o formulário individual enviado pelo Studio.

**Somente demonstração:** os dados são fictícios e ficam no `localStorage` do
navegador. Não há backend, autenticação, cobrança real ou sincronização entre
computadores. Use apenas dados fictícios no cadastro e no cartão.

## Executar

```powershell
cd projeto-2.0
npm ci
npm run dev
```

Abra `http://localhost:5183`. Rotas de apresentação:

- `/`: abre diretamente o painel de gestão.
- `/demo/conversa`: conversa fictícia com link para a mensalidade.
- `/pagar/ana-mensalidade`: dados, confirmação do plano definido pelo Studio, Pix/cartão simulados e recibo de exemplo.
- `/painel`: visão geral, cobranças, agenda e alunos.

Em **Gerar link do aluno**, os donos escolhem aluno, plano, valor e vencimento.
Depois podem copiar o link ou abrir o WhatsApp. O aluno não altera o plano ou o
valor da cobrança no formulário. Planos casal usam metade do valor total por aluno.

Nesta demonstração, os links e dados funcionam apenas no mesmo navegador/ambiente
local. Enviar o endereço localhost para outro aparelho não transfere os dados.
Acesso remoto exige hospedagem e backend; a separação das telas ainda não é
controle de acesso. O painel precisará de autenticação antes de uso real.

Visual: conteúdo claro, menu preto e dourado. O antigo Landing.tsx permanece
como referência de design, sem rota pública ou entrada no aplicativo.

Para reiniciar os exemplos, remova somente a chave `studiofd.v2.demo` do
armazenamento local deste site nas ferramentas do navegador.

## Conferir a apresentação

```powershell
npm run build
npm run preview
# Em outro terminal, nesta pasta:
node tools/shots.mjs
node tools/check-demo.mjs
```

O script usa o Google Chrome instalado no caminho padrão do Windows. Gera
imagens em 1440 px e 412 px em `video/conferencia` e falha se detectar erros
no console. A pasta `video`, dependências, builds e configurações pessoais não
entram no Git.

`check-demo.mjs` confere entrada na gestão, geração do link, preços por aluno,
CPF inválido, plano definido pelo Studio, Pix simulado, atualização entre abas
e busca sem chamadas externas. Os scripts aceitam `STUDIO_PREVIEW_URL` para
testar em outra porta sem interromper o servidor de desenvolvimento.

## Gerar o vídeo

O MP4 já existente retrata o visual anterior. Para apresentar o layout atual,
refaça a gravação e a composição com os comandos abaixo.

Com o preview aberto:

```powershell
node tools/record.mjs
..\.venv\Scripts\python.exe tools\compose_video.py --preview
..\.venv\Scripts\python.exe tools\compose_video.py
```

A composição exige Python com PySide6, numpy e imageio-ffmpeg. Também procura
dependências em `../build/video-tools`, quando disponíveis no ambiente desktop.
A trilha é sintetizada pelo próprio script. A exportação usa um arquivo
temporário, verifica vídeo e áudio do início ao fim e só então substitui
`video/Studio-FD-Link-de-Pagamento.mp4`.

## Integração futura

Os pagamentos reais ficam desativados mesmo se as variáveis de `.env.example`
forem preenchidas. O componente MercadoPagoCard é uma base reservada à próxima
etapa. Antes de habilitar cobranças, é necessário implementar o backend,
autenticar o painel e confirmar pagamentos por webhook validado e consulta à
API do provedor. A resposta do formulário nunca deve dar baixa localmente.

Access Token e Client Secret pertencem somente ao servidor. Nunca os coloque
em variáveis `VITE_*`, código do navegador ou Git. Dados reais de cartão devem
passar exclusivamente pelo SDK oficial, que envia apenas um token ao backend.

Planos, Caixa, Contratos, Relatórios e Configurações do painel web ficam para
outra etapa. A versão desktop é independente e não é alterada por este protótipo.
