// Teste do login pelo navegador. Uso: node tools/teste_login.mjs <endereço> <email-admin> <senha-admin>
import puppeteer from "puppeteer-core";

const [BASE = "http://localhost:8000", EMAIL, SENHA] = process.argv.slice(2);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const resultados = [];
const ok = (nome, cond, extra = "") => resultados.push(`${cond ? "OK   " : "FALHA"} ${nome}${!cond && extra ? `  [${extra}]` : ""}`);
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const p = await browser.newPage();
const erros = [];
p.on("pageerror", (e) => erros.push(e.message));
await p.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const texto = () => p.evaluate(() => document.body.innerText);
const tocar = async (seletor, conteudo) => {
  for (const el of await p.$$(seletor)) {
    if (!conteudo || (await el.evaluate((n) => n.textContent)).includes(conteudo)) {
      await el.evaluate((n) => { n.scrollIntoView({ block: "center" }); n.click(); });
      await wait(400);
      return true;
    }
  }
  return false;
};
const limpar = (seletor) => p.$eval(seletor, (campo) => { campo.select(); });
const entrar = async (email, senha) => {
  await limpar('input[name="email"]');
  await p.type('input[name="email"]', email);
  await limpar('input[name="senha"]');
  await p.type('input[name="senha"]', senha);
  await tocar("button.botao.ouro");
  await wait(3000);
};

await p.goto(BASE + "/", { waitUntil: "networkidle0" });
await wait(800);
ok("abre na tela de entrada", (await texto()).includes("Bem-vindo de volta"));
await p.screenshot({ path: "../conferencia/login.png" });
ok("API fechada sem login", (await p.evaluate(async () => (await fetch("/api/alunos")).status)) === 401);
await entrar(EMAIL, "senha-errada-1");
ok("senha errada mostra aviso", (await texto()).includes("E-mail ou senha incorretos"));
await entrar(EMAIL, SENHA);
ok("entra com a senha certa", (await texto()).includes("Alunos ativos"));
await p.goto(BASE + "/mais", { waitUntil: "networkidle0" });
ok("admin vê Usuários", (await texto()).includes("Quem acessa o sistema"));
await p.goto(BASE + "/mais/usuarios", { waitUntil: "networkidle0" });
await p.waitForSelector(".lista .cartao.item", { timeout: 30000 }); // espera a lista carregar (internet é mais lenta)
await wait(600);
await tocar(".botao", "Novo acesso");
await p.waitForSelector(".folha input.entrada");
const campos = await p.$$(".folha input.entrada");
const email2 = `fran${Date.now() % 100000}@teste.local`;
await campos[0].type("Fran Teste");
await campos[1].type(email2);
await campos[2].type("fran-senha-123");
await tocar(".folha .botao", "Criar acesso");
await wait(1200);
ok("cria acesso da equipe", (await texto()).includes(email2));
await p.screenshot({ path: "../conferencia/usuarios.png" });
await p.goto(BASE + "/mais/conta", { waitUntil: "networkidle0" });
await tocar(".botao", "Sair desta conta");
await wait(1200);
ok("sair volta para a entrada", (await texto()).includes("Bem-vindo de volta"));
await entrar(email2, "fran-senha-123");
ok("equipe entra", (await texto()).includes("Alunos ativos"));
await p.goto(BASE + "/mais", { waitUntil: "networkidle0" });
ok("equipe NÃO vê Usuários", !(await texto()).includes("Quem acessa o sistema"));
const sw = await p.evaluate(async () => !!(await navigator.serviceWorker?.getRegistration()));
ok("service worker instalado (PWA)", sw);
const manifesto = await p.evaluate(async () => (await fetch("/manifest.webmanifest")).json());
ok("manifesto com ícones PNG", manifesto.icons.some((i) => i.sizes === "512x512" && i.purpose === "maskable"));
ok("sem erros na página", erros.length === 0, erros.join(" | "));
await browser.close();
console.log(resultados.join("\n"));
