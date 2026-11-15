# Studio FD Performance — versão web

Protótipo local em React, TypeScript e Vite para apresentar o site do Studio,
o fluxo de mensalidades pelo celular e o painel de gestão.

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

- `/`: site, método, estrutura e planos.
- `/demo/conversa`: conversa fictícia com link para a mensalidade.
- `/pagar/ana-mensalidade`: cadastro, escolha de plano, Pix/cartão simulados e recibo de exemplo.
- `/painel`: visão geral, cobranças, agenda e alunos.

As opções de período e vencimento ilustram a experiência futura; não criam
matrícula ou reserva de horário. Planos casal são apresentados pelo valor total
no site; a mensalidade individual usa metade desse valor.

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

`check-demo.mjs` confere preços por aluno nos planos casal, bloqueio de CPF
inválido, Pix simulado, atualização entre abas e ausência de chamadas externas.

## Gerar o vídeo

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
