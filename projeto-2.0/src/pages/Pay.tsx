import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, Copy, CreditCard, Lock, QrCode, ShieldCheck } from "lucide-react";
import QRCode from "qrcode";
import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { plan as planOf, updateCharge, useDb, type Charge } from "../data/store";
import { brl, cardBrand, dateBr, maskCard, maskCpf, maskDate, maskExpiry, maskPhone, onlyDigits, validCard, validCpf } from "../lib/format";
import { EASE } from "../lib/motion";
import { API_URL, confirmPix, createPix, DEMO_MODE, MP_PUBLIC_KEY, payWithCard, type PixCharge } from "../services/payments";

// O Brick fica reservado para a etapa do backend; esta entrega só simula.
const MercadoPagoCard = lazy(() => import("../components/MercadoPagoCard"));
const USE_BRICK = !DEMO_MODE && Boolean(MP_PUBLIC_KEY && API_URL);
import "../styles/pay.css";

type Step = 0 | 1 | 2 | 3;
interface Form { name: string; cpf: string; phone: string; email: string; birth: string; terms: boolean }
const STEP_NAMES = ["Seus dados", "Seu plano", "Pagamento"];

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      <AnimatePresence>{error && <motion.small initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>{error}</motion.small>}</AnimatePresence>
    </label>
  );
}

function Stepper({ step }: { step: Step }) {
  return (
    <ol className="stepper" aria-label="Etapas">
      {STEP_NAMES.map((name, index) => (
        <li key={name} className={index < step ? "done" : index === step ? "now" : ""} aria-current={index === step ? "step" : undefined}>
          <span className="dot">{index < step ? <Check size={13} strokeWidth={3} /> : index + 1}</span>
          <span className="label">{name}</span>
          {index < 2 && <span className="bar"><motion.i animate={{ scaleX: index < step ? 1 : 0 }} transition={{ duration: 0.5, ease: EASE }} /></span>}
        </li>
      ))}
    </ol>
  );
}

function CardFace({ number, holder, expiry, cvv, flipped }: { number: string; holder: string; expiry: string; cvv: string; flipped: boolean }) {
  const brand = cardBrand(number);
  const shown = (number + " •••• •••• •••• ••••".slice(number.length)).slice(0, 19);
  return (
    <div className="card-scene" aria-hidden="true">
      <motion.div className="card-3d" animate={{ rotateY: flipped ? 180 : 0 }} transition={{ duration: 0.7, ease: EASE }}>
        <div className="card-side front">
          <div className="card-row"><span className="chip" /><span className="card-brand">{brand ?? ""}</span></div>
          <div className="card-number num">{shown}</div>
          <div className="card-row small">
            <span><i>Nome</i>{holder || "NOME NO CARTÃO"}</span>
            <span><i>Validade</i>{expiry || "MM/AA"}</span>
          </div>
        </div>
        <div className="card-side back">
          <span className="stripe" />
          <div className="cvv"><i>CVV</i><b className="num">{cvv || "•••"}</b></div>
        </div>
      </motion.div>
    </div>
  );
}

function PixPanel({ charge, onPaid }: { charge: Charge; onPaid: (id: string) => void }) {
  const [pix, setPix] = useState<PixCharge | null>(null);
  const [qr, setQr] = useState("");
  const [copied, setCopied] = useState(false);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    let alive = true;
    createPix(charge).then(async (result) => {
      const image = await QRCode.toDataURL(result.payload, { margin: 1, width: 440, color: { dark: "#0b0b0c", light: "#f3f1ec" } });
      if (alive) { setPix(result); setQr(image); }
    });
    return () => { alive = false; };
  }, [charge.id]);
  const copy = async () => {
    try { await navigator.clipboard.writeText(pix!.payload); } catch { /* sem permissão: o código continua visível */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };
  return (
    <div className="pix">
      <div className="qr">
        {qr ? <motion.img src={qr} alt="QR Code do Pix" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5, ease: EASE }} /> : <span className="qr-wait" />}
      </div>
      <ol className="pix-steps">
        <li>Este QR Code é apenas uma <b>demonstração</b>.</li>
        <li>O código não pode ser pago no banco.</li>
        <li>Simule o valor de <b>{brl(charge.cents)}</b> no botão abaixo.</li>
      </ol>
      <button className="btn block" onClick={copy} disabled={!pix}>
        {copied ? <><Check size={17} /> Código copiado</> : <><Copy size={17} /> Copiar código Pix</>}
      </button>
      <button className="btn gold block" disabled={!pix || checking} onClick={async () => { setChecking(true); onPaid(await confirmPix(charge)); }}>
        {checking ? <><span className="spin" /> Simulando pagamento…</> : "Simular pagamento Pix"}
      </button>
      <p className="hint">Nenhum valor é cobrado. O resultado fica apenas neste navegador.</p>
    </div>
  );
}

function CardPanel({ charge, onPaid }: { charge: Charge; onPaid: (id: string) => void }) {
  const [number, setNumber] = useState("");
  const [holder, setHolder] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [installments, setInstallments] = useState(1);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tried, setTried] = useState(false);
  const errors = {
    number: validCard(number) ? "" : "Confira o número do cartão.",
    holder: holder.trim().split(/\s+/).length >= 2 ? "" : "Digite o nome como está no cartão.",
    expiry: /^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry) ? "" : "Use o formato MM/AA.",
    cvv: cvv.length >= 3 ? "" : "3 ou 4 números.",
  };
  const ok = !Object.values(errors).some(Boolean);
  const submit = async () => {
    setTried(true);
    if (!ok) return;
    setBusy(true);
    onPaid(await payWithCard(charge, { number, holder, expiry, cvv, installments }));
  };
  return (
    <div className="card-form">
      <CardFace number={number} holder={holder.toUpperCase()} expiry={expiry} cvv={cvv} flipped={flipped} />
      <Field label="Número do cartão" error={tried ? errors.number : ""}>
        <input className={`input num ${tried && errors.number ? "bad" : ""}`} name="cardnumber" inputMode="numeric" autoComplete="cc-number" placeholder="0000 0000 0000 0000"
          value={number} onChange={(e) => setNumber(maskCard(e.target.value))} />
      </Field>
      <Field label="Nome impresso no cartão" error={tried ? errors.holder : ""}>
        <input className={`input ${tried && errors.holder ? "bad" : ""}`} name="ccname" autoComplete="cc-name" placeholder="Como está no cartão" value={holder} onChange={(e) => setHolder(e.target.value)} />
      </Field>
      <div className="two">
        <Field label="Validade" error={tried ? errors.expiry : ""}>
          <input className={`input num ${tried && errors.expiry ? "bad" : ""}`} name="cc-exp" inputMode="numeric" autoComplete="cc-exp" placeholder="MM/AA" value={expiry} onChange={(e) => setExpiry(maskExpiry(e.target.value))} />
        </Field>
        <Field label="CVV" error={tried ? errors.cvv : ""}>
          <input className={`input num ${tried && errors.cvv ? "bad" : ""}`} name="cvc" inputMode="numeric" autoComplete="cc-csc" placeholder="123" value={cvv}
            onFocus={() => setFlipped(true)} onBlur={() => setFlipped(false)} onChange={(e) => setCvv(onlyDigits(e.target.value).slice(0, 4))} />
        </Field>
      </div>
      <Field label="Parcelas">
        <select className="input" value={installments} onChange={(e) => setInstallments(Number(e.target.value))}>
          {[1, 2, 3].map((n) => <option key={n} value={n}>{n}x de {brl(Math.round(charge.cents / n))} sem juros</option>)}
        </select>
      </Field>
      <button className="btn gold block" onClick={submit} disabled={busy}>
        {busy ? <><span className="spin" /> Simulando…</> : <><Lock size={16} /> Simular {brl(charge.cents)}</>}
      </button>
      <p className="hint"><ShieldCheck size={14} /> Use apenas dados fictícios. Exemplo: 5031 4332 1540 6351, validade 11/28, CVV 123. Nenhuma transação é enviada ao Mercado Pago.</p>
    </div>
  );
}

function Success({ charge, receipt }: { charge: Charge; receipt: string }) {
  const message = encodeURIComponent(`Demonstração do Studio FD: simulação de ${charge.reference} (${brl(charge.cents)}), referência ${receipt}. Nenhum pagamento real foi realizado.`);
  return (
    <motion.div className="success" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <motion.div className="seal" initial={{ scale: 0.4, rotate: -30 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, damping: 14 }}>
        <svg viewBox="0 0 52 52"><motion.path d="M14 27l8 8 16-17" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.25, duration: 0.5, ease: EASE }} /></svg>
      </motion.div>
      <h1 className="serif">Simulação <em>concluída.</em></h1>
      <p className="muted">{charge.studentName.split(" ")[0] || "Aluno"}, este é um recibo de exemplo. Nenhuma mensalidade real foi paga.</p>
      <dl className="receipt">
        <div><dt>Valor</dt><dd className="num">{brl(charge.cents)}</dd></div>
        <div><dt>Forma</dt><dd>{charge.method === "pix" ? "Pix" : "Cartão de crédito"}</dd></div>
        <div><dt>Plano</dt><dd>{planOf(charge.planId).name}</dd></div>
        <div><dt>Comprovante</dt><dd className="num">{receipt}</dd></div>
      </dl>
      <a className="btn block" href={`https://wa.me/?text=${message}`} target="_blank" rel="noreferrer">Compartilhar simulação no WhatsApp</a>
      <p className="hint">Você já pode fechar esta página.</p>
    </motion.div>
  );
}

export default function Pay() {
  const { id = "" } = useParams();
  const db = useDb();
  const charge = db.charges.find((item) => item.id === id);
  const [step, setStep] = useState<Step>(0);
  const [direction, setDirection] = useState(1);
  const [method, setMethod] = useState<"pix" | "credito">("pix");
  const [receipt, setReceipt] = useState("");
  const [tried, setTried] = useState(false);
  const [form, setForm] = useState<Form>(() => ({
    name: charge?.studentName ?? "", cpf: "", phone: charge?.phone ? maskPhone(charge.phone.replace(/^55/, "")) : "", email: "", birth: "",
    terms: false,
  }));
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((current) => ({ ...current, [key]: value }));

  const errors = useMemo(() => ({
    name: form.name.trim().split(/\s+/).length >= 2 ? "" : "Digite nome e sobrenome.",
    cpf: validCpf(form.cpf) ? "" : "Confira o CPF.",
    phone: onlyDigits(form.phone).length >= 10 ? "" : "Digite o WhatsApp com DDD.",
    email: /^\S+@\S+\.\S+$/.test(form.email) ? "" : "Confira o e-mail.",
    birth: /^\d{2}\/\d{2}\/\d{4}$/.test(form.birth) ? "" : "Use dia/mês/ano.",
  }), [form]);

  if (!charge) {
    return (
      <div className="pay"><div className="pay-box missing">
        <h1 className="serif">Link não encontrado.</h1>
        <p className="muted">Este link de pagamento não existe ou já foi substituído. Peça um novo ao Studio.</p>
        <p className="hint">O formulário é enviado diretamente pelo Studio.</p>
      </div></div>
    );
  }
  const selected = planOf(charge.planId);
  const alreadyPaid = Boolean(charge.paidAt) && !receipt;
  const go = (next: Step) => { setDirection(next > step ? 1 : -1); setTried(false); setStep(next); window.scrollTo({ top: 0 }); };
  const next = () => {
    setTried(true);
    if (step === 0) {
      if (Object.values(errors).some(Boolean)) return;
      updateCharge(charge.id, { studentName: form.name.trim(), phone: `55${onlyDigits(form.phone)}` });
      go(1);
    } else if (step === 1) {
      if (!form.terms) return;
      // Plano, preço e vencimento pertencem ao link definido pelo Studio.
      go(2);
    }
  };
  const paid = (id: string) => { setReceipt(id); go(3); };

  return (
    <div className="pay">
      <header className="pay-top">
        <span className="brand"><span className="brand-mark serif">FD</span><span>Studio FD <i>Performance</i></span></span>
        <span className="secure"><Lock size={13} /> Demonstração</span>
      </header>
      {DEMO_MODE && <p className="demo-flag">Ambiente de demonstração — nenhum valor é cobrado.</p>}

      <div className="pay-grid">
        <aside className="summary">
          <p className="kicker">Mensalidade · {charge.reference}</p>
          <div className="summary-price"><span className="serif num">{brl(charge.cents)}</span></div>
          <dl>
            <div><dt>Plano</dt><dd>{selected.name}</dd></div>
            <div><dt>Frequência</dt><dd>{selected.perWeek}x na semana</dd></div>
            <div><dt>Vencimento</dt><dd>{dateBr(charge.dueDate)}</dd></div>
            <div><dt>Studio</dt><dd>FD Performance · Andradina</dd></div>
          </dl>
        </aside>

        <main className="pay-box">
          {alreadyPaid ? (
            <div className="success">
              <div className="seal"><Check size={30} strokeWidth={3} /></div>
              <h1 className="serif">Esta mensalidade <em>já foi paga.</em></h1>
              <p className="muted">Pagamento registrado em {dateBr(charge.paidAt!)}. Não é preciso fazer mais nada.</p>
            </div>
          ) : step === 3 ? (
            <Success charge={charge} receipt={receipt} />
          ) : (
            <>
              <Stepper step={step} />
              <div className="stage">
                <AnimatePresence mode="wait" custom={direction} initial={false}>
                  <motion.section key={step} custom={direction}
                    initial={{ opacity: 0, x: 34 * direction }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -34 * direction }}
                    transition={{ duration: 0.38, ease: EASE }}>
                    {step === 0 && (
                      <>
                        <h1 className="serif">Confira seus dados</h1>
                        <p className="lead">Este formulário foi preparado pelo Studio para você. Nesta demonstração, use dados fictícios.</p>
                        <div className="fields">
                          <Field label="Nome completo" error={tried ? errors.name : ""}>
                            <input className={`input ${tried && errors.name ? "bad" : ""}`} name="name" autoComplete="name" placeholder="Seu nome e sobrenome" value={form.name} onChange={(e) => set("name", e.target.value)} />
                          </Field>
                          <div className="two">
                            <Field label="CPF" error={tried ? errors.cpf : ""}>
                              <input className={`input num ${tried && errors.cpf ? "bad" : ""}`} name="cpf" inputMode="numeric" placeholder="000.000.000-00" value={form.cpf} onChange={(e) => set("cpf", maskCpf(e.target.value))} />
                            </Field>
                            <Field label="Nascimento" error={tried ? errors.birth : ""}>
                              <input className={`input num ${tried && errors.birth ? "bad" : ""}`} name="birth" inputMode="numeric" placeholder="dd/mm/aaaa" value={form.birth} onChange={(e) => set("birth", maskDate(e.target.value))} />
                            </Field>
                          </div>
                          <Field label="WhatsApp" error={tried ? errors.phone : ""}>
                            <input className={`input num ${tried && errors.phone ? "bad" : ""}`} name="tel" inputMode="tel" autoComplete="tel" placeholder="(18) 90000-0000" value={form.phone} onChange={(e) => set("phone", maskPhone(e.target.value))} />
                          </Field>
                          <Field label="E-mail" error={tried ? errors.email : ""}>
                            <input className={`input ${tried && errors.email ? "bad" : ""}`} name="email" type="email" autoComplete="email" placeholder="voce@email.com" value={form.email} onChange={(e) => set("email", e.target.value)} />
                          </Field>
                        </div>
                      </>
                    )}
                    {step === 1 && (
                      <>
                        <h1 className="serif">Seu plano no Studio</h1>
                        <p className="lead">Confira o que foi combinado. Para alterar seu plano ou vencimento, fale com o Studio.</p>
                        <dl className="receipt agreed-plan">
                          <div><dt>Plano</dt><dd>{selected.name}</dd></div>
                          <div><dt>Treinos</dt><dd>{selected.perWeek} vezes por semana</dd></div>
                          <div><dt>Mensalidade{selected.kind === "casal" ? " por aluno" : ""}</dt><dd>{brl(charge.cents)}</dd></div>
                          <div><dt>Vencimento</dt><dd>{dateBr(charge.dueDate)}</dd></div>
                        </dl>
                        <label className={`terms ${tried && !form.terms ? "bad" : ""}`}>
                          <input type="checkbox" checked={form.terms} onChange={(e) => set("terms", e.target.checked)} />
                          <span className="box"><Check size={13} strokeWidth={3.2} /></span>
                          <span>Conferi os dados e o plano combinado com o Studio.</span>
                        </label>
                      </>
                    )}
                    {step === 2 && (
                      <>
                        <h1 className="serif">Como você quer <em>pagar?</em></h1>
                        <div className="methods" role="tablist" aria-label="Forma de pagamento">
                          {([["pix", "Pix", "Aprovação na hora", QrCode], ["credito", "Cartão de crédito", "Em até 3x sem juros", CreditCard]] as const).map(([key, title, detail, Icon]) => (
                            <button key={key} role="tab" aria-selected={method === key} className={`method-tab ${method === key ? "on" : ""}`} onClick={() => setMethod(key)}>
                              {method === key && <motion.span layoutId="method-glow" className="method-glow" transition={{ type: "spring", stiffness: 360, damping: 30 }} />}
                              <Icon size={20} />
                              <span><b>{title}</b><i>{detail}</i></span>
                            </button>
                          ))}
                        </div>
                        <AnimatePresence mode="wait" initial={false}>
                          <motion.div key={method} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3, ease: EASE }}>
                            {method === "pix" ? <PixPanel charge={charge} onPaid={paid} />
                              : USE_BRICK ? <Suspense fallback={<span className="qr-wait" />}><MercadoPagoCard charge={charge} /></Suspense>
                              : <CardPanel charge={charge} onPaid={paid} />}
                          </motion.div>
                        </AnimatePresence>
                      </>
                    )}
                  </motion.section>
                </AnimatePresence>
              </div>
              {step < 2 ? (
                <div className="pay-actions">
                  {step > 0 && <button className="btn ghost" onClick={() => go((step - 1) as Step)}><ArrowLeft size={16} /> Voltar</button>}
                  <button className="btn gold block" onClick={next}>{step === 0 ? "Continuar" : "Ir para o pagamento"} <ArrowRight size={16} /></button>
                </div>
              ) : (
                <button className="btn ghost back-link" onClick={() => go(1)}><ArrowLeft size={16} /> Voltar ao plano</button>
              )}
            </>
          )}
        </main>
      </div>
      <footer className="pay-foot">Demonstração do Studio FD Performance · integração Mercado Pago prevista</footer>
    </div>
  );
}
