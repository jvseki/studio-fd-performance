// Grava o fluxo do aluno (celular) e o painel do Studio (computador) quadro a quadro,
// com os momentos de cada etapa e de cada toque. Uso: node tools/record.mjs
import puppeteer from "puppeteer-core";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = "video/quadros";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(root);
const framesPath = resolve(root, OUT);
if (framesPath !== resolve(root, "video", "quadros")) throw new Error("Pasta de gravação inválida.");
rmSync(framesPath, { recursive: true, force: true });
const BASE = process.env.STUDIO_PREVIEW_URL ?? "http://localhost:5183";
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--hide-scrollbars"] });
const log = { phone: { frames: [], marks: [], taps: [] }, desk: { frames: [], marks: [] } };
const now = () => Date.now() / 1000;

async function record(page, name, width, height) {
  mkdirSync(`${OUT}/${name}`, { recursive: true });
  const cdp = await page.createCDPSession();
  let n = 0;
  cdp.on("Page.screencastFrame", ({ data, sessionId }) => {
    const file = `${OUT}/${name}/${String(n++).padStart(5, "0")}.jpg`;
    writeFileSync(file, Buffer.from(data, "base64"));
    log[name].frames.push({ t: now(), file });
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: width, maxHeight: height, everyNthFrame: 1 });
  return cdp;
}

// ---------------------------------------------------------------- celular do aluno
const phone = await browser.newPage();
await phone.setViewport({ width: 412, height: 892, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await phone.goto(BASE + "/", { waitUntil: "networkidle0" });
await phone.evaluate(() => localStorage.clear());
await phone.goto(BASE + "/demo/conversa", { waitUntil: "networkidle0" });
const mark = (key) => log.phone.marks.push({ t: now(), key });
const tap = async (selector) => {
  const el = await phone.$(selector);
  await el.evaluate((node) => node.scrollIntoView({ behavior: "smooth", block: "center" }));
  await wait(650);
  const box = await el.boundingBox();
  log.phone.taps.push({ t: now(), x: box.x + box.width / 2, y: box.y + box.height / 2 });
  await wait(180);
  await el.click();
};
const type = async (selector, text) => { await tap(selector); await wait(250); await phone.type(selector, text, { delay: 85 }); await wait(350); };

const phoneCdp = await record(phone, "phone", 824, 1784);
mark("conversa");
await wait(4200);
await tap("#link-pagamento");
await phone.waitForSelector('input[name="cpf"]');
mark("dados");
await wait(1600);
await type('input[name="cpf"]', "52998224725");
await type('input[name="birth"]', "14031994");
await type('input[name="email"]', "ana.souza@email.com");
await wait(500);
await tap(".pay-actions .gold");
await wait(900);
mark("plano");
await wait(1300);
await tap(".terms");
await wait(900);
await tap(".pay-actions .gold");
await phone.waitForSelector(".qr img", { timeout: 8000 });
mark("pix");
await wait(1200);
await phone.evaluate(() => document.querySelector(".qr").scrollIntoView({ behavior: "smooth", block: "center" }));
await wait(3200);
await tap(".method-tab:nth-child(2)");
await wait(800);
mark("cartao");
await type('input[name="cardnumber"]', "5031433215406351");
await type('input[name="ccname"]', "Ana B Souza");
await type('input[name="cc-exp"]', "1128");
await type('input[name="cvc"]', "123");
await wait(1300);
await tap('select.input');
await wait(600);
await phone.select("select.input", "3");
await wait(1200);
await tap(".card-form .gold");
mark("processando");
await phone.waitForSelector(".success .seal", { timeout: 10000 });
await wait(300);
mark("pago");
await wait(4500);
await phoneCdp.send("Page.stopScreencast");
mark("fim");

// ---------------------------------------------------------------- painel do Studio
const desk = await browser.newPage();
await desk.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
const deskCdp = await record(desk, "desk", 1440, 900);
log.desk.marks.push({ t: now(), key: "painel" });
await desk.goto(BASE + "/painel", { waitUntil: "networkidle0" });
await wait(4200);
await desk.goto(BASE + "/painel/cobrancas", { waitUntil: "networkidle0" });
await wait(1500);
await desk.evaluate(() => [...document.querySelectorAll(".seg-row button")].find((b) => b.textContent.includes("Pagos")).click());
await wait(1600);
await desk.evaluate(() => {
  const row = [...document.querySelectorAll(".tr")].find((r) => r.textContent.includes("Ana Beatriz"));
  row?.classList.add("fresh");
  row?.scrollIntoView({ behavior: "smooth", block: "center" });
});
await wait(4200);
await deskCdp.send("Page.stopScreencast");
log.desk.marks.push({ t: now(), key: "fim" });

writeFileSync(`${OUT}/roteiro.json`, JSON.stringify(log, null, 1));
await browser.close();
console.log(`celular: ${log.phone.frames.length} quadros, painel: ${log.desk.frames.length} quadros`);
