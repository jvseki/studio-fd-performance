// Grava o uso da versão web (celular) no site publicado, quadro a quadro,
// marcando etapas e toques. Uso: node tools/gravar.mjs [endereço]
import puppeteer from "puppeteer-core";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";

const BASE = process.argv[2] ?? "https://studio-fd-demo.onrender.com";
const OUT = "../video/quadros";
rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;
const log = { frames: [], marks: [], taps: [] };

const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--hide-scrollbars"] });
const page = await browser.newPage();
await page.setViewport({ width: 412, height: 892, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
await page.goto(BASE + "/", { waitUntil: "networkidle0" });
await page.evaluate(() => { try { localStorage.removeItem("studiofd.tema"); } catch {} });
await page.reload({ waitUntil: "networkidle0" });
await wait(800);

const cdp = await page.createCDPSession();
let n = 0;
cdp.on("Page.screencastFrame", ({ data, sessionId }) => {
  const file = `${OUT}/${String(n++).padStart(5, "0")}.jpg`;
  writeFileSync(file, Buffer.from(data, "base64"));
  log.frames.push({ t: now(), file: file.replace("../", "") });
  cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
});
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 824, maxHeight: 1784, everyNthFrame: 1 });

const mark = (key) => log.marks.push({ t: now(), key });
const tap = async (seletor, texto) => {
  let alvo = null;
  for (const el of await page.$$(seletor)) {
    const visivel = await el.evaluate((n) => n.getClientRects().length > 0);
    if (visivel && (!texto || (await el.evaluate((n) => n.textContent)).includes(texto))) { alvo = el; break; }
  }
  if (!alvo) throw new Error(`não achei ${seletor} ${texto ?? ""}`);
  await alvo.evaluate((n) => n.scrollIntoView({ behavior: "smooth", block: "center" }));
  await wait(550);
  const box = await alvo.boundingBox();
  log.taps.push({ t: now(), x: box.x + box.width / 2, y: box.y + box.height / 2 });
  await wait(160);
  await alvo.click();
};
const rolar = async (y, ms = 1400) => { await page.evaluate((v) => window.scrollBy({ top: v, behavior: "smooth" }), y); await wait(ms); };

// 1. Início
mark("inicio");
await wait(2600);
await rolar(520, 1800);
await rolar(-520, 1200);

// 2. Agenda: agendar numa vaga livre
await tap('.abas a[href="/agenda"]');
await page.waitForSelector(".vaga");
mark("agenda");
await wait(1800);
await tap(".vaga.livre");
await page.waitForSelector(".folha select.entrada");
await wait(900);
const opcao = await page.$eval(".folha select.entrada", (s) => s.options[3].value);
await tap(".folha select.entrada");
await page.select(".folha select.entrada", opcao);
await wait(1100);
await tap(".folha .botao.ouro");
mark("agendado");
await wait(2600);

// 3. Alunos: pesquisa e ficha
await tap('.abas a[href="/alunos"]');
await page.waitForSelector(".busca input");
mark("alunos");
await wait(1200);
await tap(".busca input");
await page.type(".busca input", "ana", { delay: 140 });
await wait(1400);
await tap("button.cartao.item");
await page.waitForSelector(".folha .dados");
mark("ficha");
await wait(2000);
await page.evaluate(() => document.querySelector(".folha").scrollTo({ top: 900, behavior: "smooth" }));
await wait(2600);
await tap(".folha-topo button");
await wait(900);

// 4. Mensalidades: registrar pagamento
await tap('.abas a[href="/mensalidades"]');
await page.waitForSelector(".numeros");
mark("mensalidades");
await wait(1800);
await tap("button.cartao.item", "Atrasado");
await page.waitForSelector(".folha .botao.ouro");
mark("pagar");
await wait(1500);
await tap(".folha .chip", "Pix");
await wait(700);
await tap(".folha .botao.ouro");
mark("pago");
await wait(2600);

// 5. Caixa
await tap('.abas a[href="/mais"]');
await wait(900);
await tap('.lista a[href="/caixa"]');
await page.waitForSelector(".numeros");
mark("caixa");
await wait(3000);

// 6. Tema escuro
await tap('.abas a[href="/mais"]');
await page.waitForSelector(".tema");
mark("tema");
await wait(1200);
await tap(".tema button", "Escuro");
await wait(1800);
await tap('.abas a[href="/"]');
await wait(3200);
mark("fim");

await cdp.send("Page.stopScreencast");
writeFileSync("../video/roteiro.json", JSON.stringify(log, null, 1));
await browser.close();
console.log(`${log.frames.length} quadros em ${(log.frames.at(-1).t - log.frames[0].t).toFixed(1)} s · etapas: ${log.marks.map((m) => m.key).join(", ")}`);
