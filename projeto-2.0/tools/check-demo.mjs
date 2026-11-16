// Confere gestão -> link individual -> formulário, sem enviar mensagens ou cobranças.
import assert from "node:assert/strict";
import puppeteer from "puppeteer-core";

const BASE = process.env.STUDIO_PREVIEW_URL ?? "http://localhost:5183";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const errors = [], external = [];
try {
  const owner = await browser.newPage();
  function watch(page) {
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    page.on("request", (r) => { if (/^https?:/.test(r.url()) && !r.url().startsWith(BASE + "/")) external.push(r.url()); });
  }
  watch(owner);
  await owner.setViewport({ width: 1440, height: 900 });
  await owner.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await owner.goto(BASE, { waitUntil: "networkidle0" });
  assert.equal(new URL(owner.url()).pathname, "/painel", "A entrada deve ser a gestão do Studio.");
  await owner.click('.page-head a[href="/painel/cobrancas?nova=1"]');
  await owner.waitForSelector('[role="dialog"]');
  await owner.select('select[name="planId"]', "cas-2");
  assert.equal(await owner.$eval('.drawer input[inputmode="decimal"]', (el) => el.value), "300");
  await owner.select('select[name="planId"]', "cas-3");
  assert.equal(await owner.$eval('.drawer input[inputmode="decimal"]', (el) => el.value), "350");
  await owner.click(".drawer .gold");
  await owner.waitForSelector(".created-link");
  const url = await owner.$eval('.created-link input', (el) => el.value);
  const id = new URL(url).pathname.split("/").pop();
  const charge = () => owner.evaluate((id) => JSON.parse(localStorage.getItem("studiofd.v2.demo")).charges.find((c) => c.id === id), id);
  const original = await charge();
  assert.equal(original.cents, 35000);
  const page = await browser.newPage();
  watch(page);
  await page.setViewport({ width: 412, height: 860, isMobile: true, hasTouch: true });
  await page.goto(url, { waitUntil: "networkidle0" });
  assert.equal(await page.$('a[href^="/painel"]'), null, "O aluno não deve ter navegação de gestão.");
  for (const [name, value] of Object.entries({ cpf: "11111111111", birth: "14031994", email: "aluno@example.com" })) await page.type('input[name="' + name + '"]', value);
  await page.click(".pay-actions .gold");
  await page.waitForFunction(() => document.body.textContent.includes("Confira o CPF."));
  await page.click('input[name="cpf"]', { clickCount: 3 });
  await page.keyboard.press("Backspace");
  await page.type('input[name="cpf"]', "52998224725");
  await page.click(".pay-actions .gold");
  await page.waitForSelector(".agreed-plan");
  assert.equal(await page.$('[role="radio"]'), null, "O aluno só confirma o plano definido pelo Studio.");
  await page.click(".terms");
  await page.click(".pay-actions .gold");
  await page.waitForSelector(".qr img");
  assert.equal((await charge()).cents, original.cents);
  assert.equal((await charge()).dueDate, original.dueDate);
  assert.equal((await charge()).paidAt, null);
  await page.click(".pix .gold");
  await page.waitForSelector(".success .seal");
  assert.ok((await charge()).gatewayId.startsWith("DEMO-"));
  await owner.waitForFunction((id) => [...document.querySelectorAll(".tr")].some((r) => r.textContent.includes("DEMO-") && r.textContent.includes("Pago")) && JSON.parse(localStorage.getItem("studiofd.v2.demo")).charges.find((c) => c.id === id).paidAt, {}, id);
  await owner.bringToFront();
  await owner.type('.charges-toolbar input', "Ana Beatriz");
  await owner.waitForFunction(() => [...document.querySelectorAll('.tr:not(.th)')].length > 0 && [...document.querySelectorAll('.tr:not(.th)')].every((row) => row.textContent.includes("Ana Beatriz")));
  assert.ok((await owner.$$eval(".tr:not(.th)", (rows) => rows.map((r) => r.textContent))).every((text) => text.includes("Ana Beatriz")));
  await page.bringToFront();
  await page.goto(BASE + "/pagar/link-inexistente", { waitUntil: "networkidle0" });
  assert.ok(await page.$(".missing"));
  assert.equal(await page.$('a[href="/"]'), null);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  console.log("OK: entrada na gestão, link, casal por aluno, CPF, plano fixo, Pix simulado, atualização entre abas e busca. Sem chamadas externas.");
} finally {
  await browser.close();
}
