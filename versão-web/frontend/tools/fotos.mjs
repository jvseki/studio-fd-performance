// Fotografa as telas no celular e no computador. Uso: node tools/fotos.mjs ../conferencia
import puppeteer from "puppeteer-core";
const BASE = "http://localhost:5190";
const OUT = (process.argv[2] ?? "../conferencia") + "/";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const erros = [];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function foto(nome, caminho, celular, passos = async () => {}, escuro = false) {
  const p = await browser.newPage();
  await p.emulateMediaFeatures([{ name: "prefers-color-scheme", value: escuro ? "dark" : "light" }]);
  p.on("pageerror", (e) => erros.push(`${nome}: ${e.message}`));
  p.on("console", (m) => { if (m.type() === "error") erros.push(`${nome}: ${m.text()}`); });
  await p.setViewport(celular ? { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true } : { width: 1440, height: 900 });
  await p.goto(BASE + caminho, { waitUntil: "networkidle0" });
  await wait(900);
  await passos(p);
  await p.screenshot({ path: `${OUT}${nome}.png` });
  await p.close();
}
for (const [nome, caminho] of [["inicio", "/"], ["agenda", "/agenda"], ["alunos", "/alunos"], ["mensalidades", "/mensalidades"], ["caixa", "/caixa"], ["mais", "/mais"]]) {
  await foto(`cel-${nome}`, caminho, true);
}
await foto("cel-ficha", "/alunos", true, async (p) => { await p.click("button.cartao.item"); await wait(1200); });
await foto("cel-pagar", "/mensalidades", true, async (p) => {
  const itens = await p.$$("button.cartao.item");
  for (const item of itens) { if ((await item.evaluate((n) => n.textContent)).includes("Atrasado") || (await item.evaluate((n) => n.textContent)).includes("Pendente")) { await item.click(); break; } }
  await wait(1200);
});
await foto("cel-agendar", "/agenda", true, async (p) => { await p.click(".vaga.livre"); await wait(1200); });
await foto("pc-inicio", "/", false);
for (const [nome, caminho] of [["inicio", "/"], ["agenda", "/agenda"], ["alunos", "/alunos"], ["caixa", "/caixa"], ["mais", "/mais"]]) {
  await foto(`escuro-${nome}`, caminho, true, async () => {}, true);
}
await foto("escuro-pagar", "/mensalidades", true, async (p) => { await p.click("button.cartao.item"); await wait(1200); }, true);
await foto("escuro-pc-agenda", "/agenda", false, async () => {}, true);
await foto("pc-agenda", "/agenda", false);
await browser.close();
console.log(erros.length ? "ERROS:\n" + erros.join("\n") : "sem erros no console");
