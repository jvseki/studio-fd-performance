// Teste completo do site publicado: abre como usuário (celular e computador,
// tema claro e escuro), passa por todas as telas e ações, e confere a API.
// Uso: node tools/teste_completo.mjs [endereço]
import puppeteer from "puppeteer-core";

const BASE = process.argv[2] ?? "https://studio-fd-demo.onrender.com";
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const resultados = [];
const ok = (nome, cond, detalhe = "") => resultados.push({ nome, ok: !!cond, detalhe });
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });

async function abrir(celular, escuro) {
  const p = await browser.newPage();
  p.erros = [];
  p.on("pageerror", (e) => p.erros.push(e.message));
  // "Failed to load resource" de 4xx é o navegador registrando uma recusa da API; as recusas são conferidas à parte.
  p.on("console", (m) => { if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) p.erros.push(m.text()); });
  p.on("response", async (r) => {
    if (r.status() >= 500) p.erros.push(`HTTP ${r.status()} ${r.url()}`);
    else if (r.status() >= 400 && r.url().includes("/api/")) p.avisos4xx = [...(p.avisos4xx ?? []), `${r.status()} ${r.request().method()} ${r.url().replace(BASE, "")} ${await r.text().catch(() => "")}`];
  });
  await p.setViewport(celular ? { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true } : { width: 1366, height: 800 });
  await p.emulateMediaFeatures([{ name: "prefers-color-scheme", value: escuro ? "dark" : "light" }]);
  return p;
}
const texto = (p) => p.evaluate(() => document.body.innerText);
const tocar = async (el) => { await el.evaluate((n) => { n.scrollIntoView({ block: "center" }); n.click(); }); await wait(250); };
const clicarTexto = async (p, seletor, conteudo) => {
  for (const el of await p.$$(seletor)) {
    const visivel = await el.evaluate((n) => n.getClientRects().length > 0);
    if (visivel && (await el.evaluate((n) => n.textContent)).includes(conteudo)) { await tocar(el); return true; }
  }
  return false;
};
const sem_vazamento = (p) => p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

// ---------------------------------------------------------------- 1. telas em 4 combinações
for (const [celular, escuro] of [[true, false], [true, true], [false, false], [false, true]]) {
  const nome = `${celular ? "celular" : "computador"} ${escuro ? "escuro" : "claro"}`;
  const p = await abrir(celular, escuro);
  for (const [rota, esperado] of [["/", "Alunos ativos"], ["/agenda", "Douglas"], ["/alunos", "Inativos"], ["/mensalidades", "Recebido"],
    ["/caixa", "Saldo"], ["/mais", "Aparência"], ["/mais/planos", "Individual 3x"], ["/mais/relatorios", "Últimos 6 meses"],
    ["/mais/configuracoes", "Funcionamento"], ["/mais/backup", "Baixar backup"]]) {
    await p.goto(BASE + rota, { waitUntil: "networkidle0" });
    await wait(500);
    ok(`${nome}: ${rota} abre`, (await texto(p)).includes(esperado), esperado);
    ok(`${nome}: ${rota} sem rolagem lateral`, await sem_vazamento(p));
  }
  const fundo = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
  ok(`${nome}: cor de fundo do tema`, escuro ? fundo === "rgb(14, 14, 16)" : fundo === "rgb(246, 244, 239)", fundo);
  ok(`${nome}: sem erros no console`, p.erros.length === 0, p.erros.join(" | "));
  await p.close();
}

// ---------------------------------------------------------------- 2. fluxos no celular
const p = await abrir(true, false);
const nome = `Teste Completo ${Date.now().toString().slice(-5)}`;
await p.goto(BASE + "/alunos", { waitUntil: "networkidle0" });
await tocar(await p.$(".flutuante"));
await p.waitForSelector(".folha input.entrada");
await wait(500);
const campos = await p.$$(".folha input.entrada");
await campos[0].type(nome);
await campos[1].type("18998887777");
await p.select(".folha select.entrada", (await p.$eval(".folha select.entrada", (s) => s.options[2].value)));
await wait(300);
const valorPlano = await p.$eval(".folha input[inputmode=decimal]", (i) => i.value);
ok("cadastro: plano preenche o valor sozinho", valorPlano.length > 0, valorPlano);
await campos[3].type("12");
await clicarTexto(p, ".folha .botao", "Salvar");
await wait(1500);
ok("cadastro: aluno novo aparece na lista", (await texto(p)).includes(nome));

await p.type(".busca input", nome.slice(-5));
await wait(1200);
ok("pesquisa: encontra pelo pedaço do nome", (await p.$$("button.cartao.item")).length === 1);
await tocar(await p.$("button.cartao.item"));
await p.waitForSelector(".folha .dados");
ok("ficha: abre com dados", (await texto(p)).includes("Dia 12"));
const input = await p.$('.folha input[type="file"]');
const pdf = Buffer.from("%PDF-1.4\n% teste completo\n%%EOF\n");
const fs = await import("node:fs");
fs.writeFileSync("teste-anamnese.pdf", pdf);
await input.uploadFile("teste-anamnese.pdf");
await wait(2000);
ok("ficha: anexa anamnese em PDF", (await texto(p)).includes("teste-anamnese.pdf"));
fs.writeFileSync("falso.pdf", "isto nao e pdf");
await input.uploadFile("falso.pdf");
await wait(1800);
ok("ficha: recusa arquivo que não é PDF", (await texto(p)).includes("não é um PDF"));
fs.unlinkSync("teste-anamnese.pdf"); fs.unlinkSync("falso.pdf");
await tocar(await p.$(".folha-topo button"));
await wait(600);

// agenda: agendar e checar limite
await p.goto(BASE + "/agenda", { waitUntil: "networkidle0" });
await tocar(await p.$(".dia:nth-child(7)")); // domingo da semana: costuma estar vazio
await wait(1200);
const livres = await p.$$(".vaga.livre");
await tocar(livres[0]);
await p.waitForSelector(".folha select.entrada");
const opcoes = await p.$$eval(".folha select.entrada option", (os) => os.map((o) => [o.value, o.textContent]));
await p.select(".folha select.entrada", opcoes.find(([, t]) => t === nome)[0]);
await clicarTexto(p, ".folha .opcao", "Horário fixo"); // agenda só este dia
await clicarTexto(p, ".folha .botao", "Agendar");
await wait(1800);
ok("agenda: aluno agendado aparece na vaga", (await texto(p)).includes(nome));
const outro = opcoes.find(([v, t]) => v && t !== nome)[0];
await tocar((await p.$$(".vaga.livre"))[0]);
await p.waitForSelector(".folha select.entrada");
await p.select(".folha select.entrada", outro);
await clicarTexto(p, ".folha .opcao", "Horário fixo");
await clicarTexto(p, ".folha .botao", "Agendar");
await wait(1800);
const cheio = await p.evaluate(() => document.querySelector(".horario .vagas")?.querySelectorAll(".vaga.cheia").length);
ok("agenda: segundo aluno no mesmo horário entra", cheio === 2, String(cheio));
await tocar(await p.$(".vaga.cheia"));
await p.waitForSelector(".folha");
await clicarTexto(p, ".folha .botao", "Compareceu");
await wait(1500);
ok("agenda: marcar compareceu", (await texto(p)).includes("Concluído"));

// mensalidades: gerar, pagar e desfazer
await p.goto(BASE + "/mensalidades", { waitUntil: "networkidle0" });
await clicarTexto(p, ".botao", "Gerar do mês");
await wait(1800);
ok("mensalidades: gerar do mês inclui o aluno novo", (await texto(p)).includes(nome));
const antes = await (await fetch(BASE + "/api/caixa")).json();
const achou = await clicarTexto(p, "button.cartao.item", nome);
if (!(await p.waitForSelector(".folha .botao.ouro", { timeout: 8000 }).catch(() => null))) {
  await p.screenshot({ path: "../conferencia/falha-mensalidade.png", fullPage: true });
  console.log("DEPURAÇÃO: achou o aluno na lista?", achou, "| recusas:", p.avisos4xx ?? []);
  throw new Error("folha de pagamento não abriu");
}
await clicarTexto(p, ".folha .chip", "Dinheiro");
await clicarTexto(p, ".folha .botao", "Confirmar");
await wait(1800);
const depois = await (await fetch(BASE + "/api/caixa")).json();
ok("mensalidades: pagamento entra no caixa", depois.entradas > antes.entradas, `${antes.entradas} -> ${depois.entradas}`);
p.on("dialog", (d) => d.accept());
await clicarTexto(p, "button.cartao.item", nome);
await p.waitForSelector(".folha");
await clicarTexto(p, ".folha .botao", "Desfazer");
await wait(1800);
const desfeito = await (await fetch(BASE + "/api/caixa")).json();
ok("mensalidades: desfazer tira do caixa", desfeito.entradas === antes.entradas, `${desfeito.entradas}`);

// caixa: lançar saída e excluir
await p.goto(BASE + "/caixa", { waitUntil: "networkidle0" });
await clicarTexto(p, ".botao", "Saída");
await p.waitForSelector(".folha input.entrada");
const cx = await p.$$(".folha input.entrada");
await cx[0].type("Teste completo saída");
await cx[1].type("12,34");
await clicarTexto(p, ".folha .botao", "Lançar");
await wait(1500);
ok("caixa: lançar saída", (await texto(p)).includes("Teste completo saída"));
for (const item of await p.$$(".cartao.item")) {
  if ((await item.evaluate((n) => n.textContent)).includes("Teste completo saída")) { await tocar(await item.$("button")); break; }
}
await wait(1500);
ok("caixa: excluir movimentação", !(await texto(p)).includes("Teste completo saída"));

// tema escolhido fica salvo
await p.goto(BASE + "/mais", { waitUntil: "networkidle0" });
await clicarTexto(p, ".tema button", "Escuro");
await p.reload({ waitUntil: "networkidle0" });
ok("tema: escolha fica salva ao recarregar", (await p.evaluate(() => document.documentElement.dataset.tema)) === "escuro");
ok("fluxos: sem erros no console", p.erros.length === 0, p.erros.join(" | "));
console.log("Recusas da API durante os fluxos:", p.avisos4xx ?? []);
await p.close();

// ---------------------------------------------------------------- 3. PWA e API
const manifesto = await (await fetch(BASE + "/manifest.webmanifest")).json().catch(() => null);
ok("PWA: manifesto para instalar no tablet", manifesto?.display === "standalone", manifesto?.name);
ok("API: endereço inexistente responde 404", (await fetch(BASE + "/api/nao-existe")).status === 404);
ok("API: dado inválido vira mensagem (400)", (await fetch(BASE + "/api/mensalidades?mes_ref=abc")).status === 400);
const bkp = await fetch(BASE + "/api/backup");
ok("backup: baixa arquivo .fdbkp", bkp.status === 200 && (bkp.headers.get("content-disposition") ?? "").includes(".fdbkp"));
const inicio = Date.now();
await fetch(BASE + "/api/resumo");
ok("velocidade: resumo responde em menos de 2 s", Date.now() - inicio < 2000, `${Date.now() - inicio} ms`);

await browser.close();
const falhas = resultados.filter((x) => !x.ok);
for (const x of resultados) console.log(`${x.ok ? "OK   " : "FALHA"} ${x.nome}${x.detalhe && !x.ok ? `  [${x.detalhe}]` : ""}`);
console.log(`\n${resultados.length - falhas.length} de ${resultados.length} verificações passaram.`);
process.exitCode = falhas.length ? 1 : 0;
