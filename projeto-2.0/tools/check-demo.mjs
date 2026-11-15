// Confere o preço por aluno e a baixa simulada, sem enviar mensagens ou cobranças.
// Uso: node tools/check-demo.mjs (com npm run preview aberto).
import assert from "node:assert/strict";
import puppeteer from "puppeteer-core";

const BASE = "http://localhost:5183";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const errors = [];
const external = [];
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => { if (/^https?:/.test(r.url()) && !r.url().startsWith(BASE + "/")) external.push(r.url()); });
  await page.setViewport({ width: 1440, height: 900 });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.goto(BASE, { waitUntil: "networkidle0" });
  await page.click('.seg [role="tab"]:nth-child(2)');
  await page.waitForSelector(".plan-grid.casal .plan .gold");
  await page.click(".plan-grid.casal .plan .gold");
  await page.waitForSelector('input[name="cpf"]');
  const id = new URL(page.url()).pathname.split("/").pop();
  const charge = () => page.evaluate((id) => JSON.parse(localStorage.getItem("studiofd.v2.demo")).charges.find((c) => c.id === id), id);
  assert.equal((await charge()).cents, 30000, "Casal 2x deve começar em R$ 300 por aluno.");
  for (const [name, value] of Object.entries({ name: "Aluno Exemplo", cpf: "11111111111", birth: "14031994", tel: "18997000000", email: "aluno@example.com" })) {
    await page.type(`input[name="${name}"]`, value);
  }
  await page.click(".pay-actions .gold");
  await page.waitForFunction(() => document.body.textContent.includes("Confira o CPF."));
  assert.ok(await page.$('input[name="cpf"]'), "CPF inválido não pode avançar.");
  await page.click('input[name="cpf"]', { clickCount: 3 });
  await page.keyboard.press("Backspace");
  await page.type('input[name="cpf"]', "52998224725");
  await page.click(".pay-actions .gold");
  await page.waitForSelector('[role="radio"]');
  await page.click('[role="radio"]:nth-child(2)');
  await page.click(".terms");
  await page.click(".pay-actions .gold");
  await page.waitForSelector(".qr img");
  assert.equal((await charge()).cents, 35000, "Trocar para Casal 3x deve custar R$ 350 por aluno.");
  assert.equal((await charge()).paidAt, null, "Gerar QR de exemplo não deve dar baixa.");
  const panel = await browser.newPage();
  await panel.goto(BASE + "/painel/cobrancas", { waitUntil: "networkidle0" });
  await page.bringToFront();
  await page.click(".pix .gold");
  await page.waitForSelector(".success .seal");
  const result = await charge();
  assert.ok(result.paidAt);
  assert.ok(result.gatewayId.startsWith("DEMO-"));
  await panel.waitForFunction(() => [...document.querySelectorAll(".tr")].some((row) => row.textContent.includes("Aluno Exemplo") && row.textContent.includes("Pago")));
  const stored = await page.evaluate(() => localStorage.getItem("studiofd.v2.demo"));
  assert.ok(!stored.includes("529.982.247-25"), "CPF não deve persistir na demonstração.");
  await page.goto(BASE + "/pagar/link-inexistente", { waitUntil: "networkidle0" });
  assert.ok(await page.$(".missing"));
  assert.deepEqual(errors, []);
  assert.deepEqual(external, [], "A simulação não deve chamar serviços externos.");
  console.log("OK: plano casal, CPF inválido, Pix simulado, atualização entre abas e link inexistente. Nenhuma chamada externa.");
} finally {
  await browser.close();
}
