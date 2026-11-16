// Fotografa as telas para conferência visual. Uso: node tools/shots.mjs <pasta>
import puppeteer from "puppeteer-core";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "video/conferencia";
mkdirSync(out, { recursive: true });
const BASE = process.env.STUDIO_PREVIEW_URL ?? "http://localhost:5183";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--hide-scrollbars"] });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];

async function desktop(name, path, steps = async () => {}) {
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: ${m.text()}`); });
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  await page.goto(BASE + path, { waitUntil: "networkidle0" });
  await wait(2200);
  await steps(page);
  await page.screenshot({ path: `${out}/${name}.png` });
  await page.close();
}
await desktop("01-inicio", "/");
await desktop("02-gerar-link", "/painel/cobrancas?nova=1");
await desktop("07-painel", "/painel");
await desktop("08-cobrancas", "/painel/cobrancas");
await desktop("09-agenda", "/painel/agenda");
await desktop("10-alunos", "/painel/alunos");
await desktop("11-pagar-desktop", "/pagar/ana-mensalidade");

const phone = await browser.newPage();
phone.on("pageerror", (e) => errors.push(`celular: ${e.message}`));
phone.on("console", (m) => { if (m.type() === "error") errors.push(`celular: ${m.text()}`); });
await phone.setViewport({ width: 412, height: 860, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await phone.goto(BASE + "/pagar/ana-mensalidade", { waitUntil: "networkidle0" });
await wait(1200);
await phone.screenshot({ path: `${out}/12-celular-dados.png` });
await phone.type('input[name="cpf"]', "52998224725");
await phone.type('input[name="birth"]', "14031994");
await phone.type('input[name="email"]', "ana@email.com");
await phone.click(".pay-actions .gold");
await wait(900);
await phone.click(".terms");
await phone.screenshot({ path: `${out}/13-celular-plano.png` });
await phone.click(".pay-actions .gold");
await wait(1800);
await phone.screenshot({ path: `${out}/14-celular-pix.png` });
await phone.click(".method-tab:nth-child(2)");
await wait(700);
await phone.type('input[name="cardnumber"]', "5031433215406351");
await phone.type('input[name="ccname"]', "Ana B Souza");
await phone.type('input[name="cc-exp"]', "1128");
await phone.screenshot({ path: `${out}/15-celular-cartao.png` });
await phone.type('input[name="cvc"]', "123");
await wait(900);
await phone.screenshot({ path: `${out}/16-celular-cvv.png` });
await phone.click(".card-form .gold");
await wait(3600);
await phone.screenshot({ path: `${out}/17-celular-pago.png` });
await phone.goto(BASE + "/demo/conversa", { waitUntil: "networkidle0" });
await wait(3600);
await phone.screenshot({ path: `${out}/18-conversa.png` });
for (const [name, path] of [["19-celular-inicio", "/"], ["20-celular-gerar-link", "/painel/cobrancas?nova=1"], ["21-celular-cobrancas", "/painel/cobrancas"], ["22-celular-agenda", "/painel/agenda"], ["23-celular-alunos", "/painel/alunos"]]) {
  await phone.goto(BASE + path, { waitUntil: "networkidle0" });
  await wait(2200);
  await phone.screenshot({ path: `${out}/${name}.png` });
}
await browser.close();
console.log(errors.length ? "ERROS:\n" + errors.join("\n") : "sem erros no console");
process.exitCode = errors.length ? 1 : 0;
