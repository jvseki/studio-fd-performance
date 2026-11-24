// Confere a parte "Versão PWA" no Mais em Android, iPhone e computador.
// Uso: node tools/teste_pwa.mjs <endereço> <email> <senha> <pasta-das-fotos>
import puppeteer from "puppeteer-core";

const [BASE = "http://localhost:8000", EMAIL, SENHA, PASTA = "."] = process.argv.slice(2);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const aparelhos = {
  android: { ua: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36", vp: { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, espera: "Instalar app" },
  iphone: { ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", vp: { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, espera: "Adicionar à Tela de Início" },
  computador: { ua: null, vp: { width: 1280, height: 800 }, espera: "Instalar página como app" },
};
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
for (const [nome, a] of Object.entries(aparelhos)) {
  const ctx = await browser.createBrowserContext();
  const p = await ctx.newPage();
  const erros = [];
  p.on("pageerror", (e) => erros.push(e.message));
  if (a.ua) await p.setUserAgent(a.ua);
  await p.setViewport(a.vp);
  await p.goto(BASE + "/", { waitUntil: "networkidle0" });
  await p.type('input[name="email"]', EMAIL);
  await p.type('input[name="senha"]', SENHA);
  await p.$eval("button.botao.ouro", (n) => n.click());
  await wait(2500);
  const inicio = await p.evaluate(() => document.body.innerText);
  await p.goto(BASE + "/mais", { waitUntil: "networkidle0" });
  await wait(800);
  const mais = await p.evaluate(() => document.body.innerText);
  const ok = mais.includes("Versão PWA") && mais.includes(a.espera) && !inicio.includes("Instalar app") && erros.length === 0;
  console.log(`${ok ? "OK   " : "FALHA"} ${nome}${erros.length ? "  " + erros.join(" | ") : ""}`);
  await p.screenshot({ path: `${PASTA}/pwa-${nome}.png` });
  await ctx.close();
}
await browser.close();
