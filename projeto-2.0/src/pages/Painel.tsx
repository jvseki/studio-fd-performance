import { animate, AnimatePresence, motion } from "motion/react";
import { ArrowDownLeft, ArrowUpRight, CalendarDays, Check, ChevronLeft, ChevronRight, Copy, ExternalLink, LayoutGrid, Link2, Plus, RotateCcw, Search, Send, Undo2, Users, Wallet, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, useSearchParams } from "react-router-dom";
import {
  addSession, chargeStatus, createCharge, markPaid, markSent, payLink, plan, PLANS, resetDemo, setSessionStatus, TIMES, today, TRAINERS, undoPaid, useDb,
  type Charge, type ChargeStatus, type Session,
} from "../data/store";
import { brl, dateBr, initials, maskPhone, onlyDigits } from "../lib/format";
import { EASE } from "../lib/motion";
import "../styles/painel.css";

const STATUS_LABEL: Record<ChargeStatus, string> = { pago: "Pago", pendente: "Pendente", atrasado: "Atrasado" };
const STATUS_TONE: Record<ChargeStatus, string> = { pago: "ok", pendente: "gold", atrasado: "danger" };
const firstOfMonth = () => today().slice(0, 8) + "01";

function Count({ value, money = false }: { value: number; money?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      if (ref.current) ref.current.textContent = money ? brl(value) : String(value);
      previous.current = value;
      return;
    }
    const controls = animate(previous.current, value, {
      duration: 0.9, ease: EASE,
      onUpdate: (v) => { if (ref.current) ref.current.textContent = money ? brl(Math.round(v)) : String(Math.round(v)); },
    });
    previous.current = value;
    return () => controls.stop();
  }, [value, money]);
  return <span ref={ref} className="num">{money ? brl(value) : value}</span>;
}

function whatsapp(charge: Charge) {
  const first = charge.studentName.split(" ")[0];
  const text = `Olá, ${first}! Aqui é do Studio FD Performance. Segue o link da mensalidade de ${charge.reference} (${brl(charge.cents)}): ${payLink(charge.id)}`;
  return `https://wa.me/${charge.phone}?text=${encodeURIComponent(text)}`;
}

export function PainelLayout() {
  return (
    <div className="painel">
      <aside className="side">
        <Link to="/painel" className="brand"><span className="brand-mark serif">FD</span><span>Studio FD <i>Performance</i></span></Link>
        <p className="nav-label">Gestão do Studio</p>
        <nav aria-label="Menu do Studio">
          <NavLink end to="/painel"><LayoutGrid size={17} /> Início</NavLink>
          <NavLink to="/painel/cobrancas"><Wallet size={17} /> Cobranças</NavLink>
          <NavLink to="/painel/agenda"><CalendarDays size={17} /> Agenda</NavLink>
          <NavLink to="/painel/alunos"><Users size={17} /> Alunos</NavLink>
        </nav>
        <div className="side-foot">
          <span className="demo-tag">Versão de demonstração</span>
          <p>Explore com dados de exemplo, salvos neste navegador.</p>
          <button className="btn sm ghost" onClick={() => { if (window.confirm("Restaurar os exemplos? As alterações desta demonstração serão apagadas.")) resetDemo(); }}><RotateCcw size={14} /> Restaurar exemplos</button>
        </div>
        <div className="studio-profile"><span className="avatar">FD</span><span><b>Douglas & Fran</b><small>Administração do Studio</small></span></div>
      </aside>
      <div className="workspace">
        <header className="workspace-bar"><span><span className="online-dot" /> Área de gestão</span><span className="workspace-note">Studio FD Performance <i> / </i> Andradina · SP</span></header>
        <main className="content" id="conteudo"><Outlet /></main>
        <footer className="workspace-footer">Studio FD Performance <span>Demonstração · pagamentos simulados</span></footer>
      </div>
    </div>
  );
}

function Page({ kicker, title, action, children }: { kicker: string; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}>
      <header className="page-head">
        <div><p className="kicker">{kicker}</p><h1>{title}</h1></div>
        {action}
      </header>
      {children}
    </motion.div>
  );
}

export function Overview() {
  const db = useDb();
  const month = db.charges.filter((c) => c.dueDate >= firstOfMonth());
  const received = db.charges.filter((c) => c.paidAt && c.paidAt >= firstOfMonth());
  const overdue = db.charges.filter((c) => chargeStatus(c) === "atrasado");
  const pending = month.filter((c) => chargeStatus(c) === "pendente");
  const todaySessions = db.sessions.filter((s) => s.day === today());
  const recent = [...db.charges].filter((c) => c.paidAt).sort((a, b) => (b.paidAt! + b.id).localeCompare(a.paidAt! + a.id)).slice(0, 6);
  const kpis = [
    { label: "Recebido no mês", value: received.reduce((sum, c) => sum + c.cents, 0), money: true, note: `${received.length} pagamento(s)`, accent: true },
    { label: "A receber", value: pending.reduce((sum, c) => sum + c.cents, 0), money: true, note: `${pending.length} dentro do prazo` },
    { label: "Em atraso", value: overdue.reduce((sum, c) => sum + c.cents, 0), money: true, note: `${overdue.length} mensalidade(s)` },
    { label: "Atendimentos hoje", value: todaySessions.length, note: `de ${TIMES.length * TRAINERS.length} vagas` },
  ];
  return (
    <Page kicker={new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })} title="Seu Studio, em dia." action={<Link className="btn gold" to="/painel/cobrancas?nova=1"><Plus size={17} /> Gerar link do aluno</Link>}>
      <p className="page-description">Acompanhe os atendimentos e as mensalidades em um só lugar.</p>
      <div className="kpis">
        {kpis.map((kpi, index) => (
          <motion.div className={`kpi ${kpi.accent ? "accent" : ""}`} key={kpi.label} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.07, duration: 0.5, ease: EASE }}>
            <div className="kpi-label"><span>{kpi.label}</span>{index === 0 ? <ArrowDownLeft size={18} /> : index === 3 ? <CalendarDays size={18} /> : <Wallet size={18} />}</div>
            <strong><Count value={kpi.value} money={kpi.money} /></strong>
            <span className="faint">{kpi.note}</span>
          </motion.div>
        ))}
      </div>
      <div className="daily-actions">
        <Link to="/painel/agenda"><span className="action-icon"><CalendarDays size={21} /></span><span><b>Organizar os atendimentos</b><small>Veja horários e marque presenças</small></span><ArrowUpRight size={18} /></Link>
        <Link to="/painel/cobrancas?filtro=atrasado"><span className="action-icon"><Wallet size={21} /></span><span><b>{overdue.length ? `${overdue.length} mensalidades precisam de atenção` : "Mensalidades em dia"}</b><small>Consulte pendências e envie o link ao aluno</small></span><ArrowUpRight size={18} /></Link>
      </div>
      <div className="split">
        <section className="panel">
          <div className="panel-head"><h2>Pagamentos recentes</h2><Link className="btn sm ghost" to="/painel/cobrancas">Ver cobranças</Link></div>
          <ul className="rows">
            <AnimatePresence initial={false}>
              {recent.map((charge) => (
                <motion.li key={charge.id} layout initial={{ opacity: 0, x: -14, backgroundColor: "rgba(201,169,107,.18)" }} animate={{ opacity: 1, x: 0, backgroundColor: "rgba(201,169,107,0)" }} transition={{ duration: 0.9, ease: EASE }}>
                  <span className="avatar">{initials(charge.studentName)}</span>
                  <span className="grow"><b>{charge.studentName}</b><i>{plan(charge.planId).name} · {charge.reference}</i></span>
                  <span className="pill">{charge.method === "pix" ? "Pix" : "Cartão"}</span>
                  <span className="num amount">{brl(charge.cents)}</span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Agenda de hoje</h2><Link className="btn sm ghost" to="/painel/agenda">Abrir</Link></div>
          <div className="mini-agenda">
            <div className="mini-row head"><span /> {TRAINERS.map((t) => <span key={t}>{t}</span>)}</div>
            {TIMES.filter((time) => todaySessions.some((s) => s.time === time)).slice(0, 7).map((time) => (
              <div className="mini-row" key={time}>
                <span className="num">{time}</span>
                {TRAINERS.map((trainer) => {
                  const session = todaySessions.find((s) => s.time === time && s.trainer === trainer);
                  return <span key={trainer} className={session ? "slot" : "slot free"}>{session?.studentName.split(" ").slice(0, 2).join(" ") ?? "Livre"}</span>;
                })}
              </div>
            ))}
          </div>
        </section>
      </div>
    </Page>
  );
}

function NewCharge({ onClose }: { onClose: (created?: Charge) => void }) {
  const db = useDb();
  const [studentId, setStudentId] = useState(db.students[0]?.id ?? "");
  const student = db.students.find((s) => s.id === studentId);
  const [planId, setPlanId] = useState(student?.planId ?? "ind-3");
  const [value, setValue] = useState(String(plan(planId).cents / (plan(planId).kind === "casal" ? 200 : 100)));
  const drawerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    drawerRef.current?.querySelector<HTMLElement>("button")?.focus();
    return () => previous?.focus();
  }, []);
  const [due, setDue] = useState(() => { const d = new Date(); d.setDate(d.getDate() + 5); return d.toISOString().slice(0, 10); });
  useEffect(() => { if (student) { setPlanId(student.planId); setValue(String(plan(student.planId).cents / (plan(student.planId).kind === "casal" ? 200 : 100))); } }, [studentId]);
  const cents = Math.round(Number(value.replace(",", ".")) * 100);
  return (
    <motion.div className="drawer-wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => onClose()}>
      <motion.aside ref={drawerRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="new-charge-title" initial={{ x: 420 }} animate={{ x: 0 }} exit={{ x: 420 }} transition={{ duration: 0.25, ease: EASE }} onClick={(e) => e.stopPropagation()} onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
        if (e.key === "Tab") {
          const items = [...drawerRef.current!.querySelectorAll<HTMLElement>('button:not(:disabled), input, select, a[href]')];
          const first = items[0], last = items[items.length - 1];
          if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
          if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
      }}>
        <div className="panel-head"><h2 id="new-charge-title">Gerar link do aluno</h2><button className="btn sm ghost" aria-label="Fechar" onClick={() => onClose()}><X size={16} /></button></div>
        <p className="muted">Defina a mensalidade. O aluno recebe somente o formulário para conferir os dados e continuar.</p>
        <label className="field"><span>Aluno</span>
          <select name="studentId" className="input" value={studentId} onChange={(e) => setStudentId(e.target.value)}>{db.students.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        </label>
        <label className="field"><span>Plano</span>
          <select name="planId" className="input" value={planId} onChange={(e) => { setPlanId(e.target.value); const chosen = plan(e.target.value); setValue(String(chosen.cents / (chosen.kind === "casal" ? 200 : 100))); }}>{PLANS.map((p) => <option key={p.id} value={p.id}>{p.name} — {brl(p.cents / (p.kind === "casal" ? 2 : 1))} por aluno</option>)}</select>
        </label>
        <div className="two">
          <label className="field"><span>Valor (R$)</span><input className="input num" inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} /></label>
          <label className="field"><span>Vencimento</span><input className="input num" type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
        </div>
        <p className="faint small">Demonstração: o link funciona neste computador. O envio para outros aparelhos será habilitado com a hospedagem.</p>
        <button className="btn gold block" disabled={!student || !Number.isFinite(cents) || !(cents > 0) || !due} onClick={() => onClose(createCharge({ studentId, studentName: student!.name, phone: `55${onlyDigits(student!.phone.replace(/^55/, ""))}`, planId, cents, dueDate: due }))}>
          <Link2 size={17} /> Criar link
        </button>
      </motion.aside>
    </motion.div>
  );
}

export function Charges() {
  const db = useDb();
  const [params, setParams] = useSearchParams();
  const initialFilter = params.get("filtro");
  const [filter, setFilter] = useState<"todas" | ChargeStatus>(initialFilter === "atrasado" ? "atrasado" : "todas");
  const [creating, setCreating] = useState(params.get("nova") === "1");
  const [query, setQuery] = useState("");
  const [created, setCreated] = useState<Charge | null>(null);
  const [copyError, setCopyError] = useState("");
  const [copied, setCopied] = useState("");
  const [fresh, setFresh] = useState("");
  const list = useMemo(() => [...db.charges].filter((c) => c.studentName && c.studentName.toLocaleLowerCase("pt-BR").includes(query.toLocaleLowerCase("pt-BR").trim()) && (filter === "todas" || chargeStatus(c) === filter))
    .sort((a, b) => b.dueDate.localeCompare(a.dueDate) || a.studentName.localeCompare(b.studentName)), [db.charges, filter, query]);
  const copy = async (charge: Charge) => {
    setCopyError("");
    try { await navigator.clipboard.writeText(payLink(charge.id)); } catch { setCopyError("Não foi possível copiar. Abra o formulário e copie o endereço do navegador."); return; }
    setCopied(charge.id); setTimeout(() => setCopied(""), 1800);
  };
  const counts = { todas: db.charges.filter((c) => c.studentName).length, atrasado: 0, pendente: 0, pago: 0 } as Record<string, number>;
  db.charges.forEach((c) => { if (c.studentName) counts[chargeStatus(c)]++; });
  return (
    <Page kicker="Mensalidades e links dos alunos" title="Cobranças" action={<button className="btn gold" onClick={() => setCreating(true)}><Plus size={16} /> Gerar link do aluno</button>}>
      {copyError && <p className="alert" role="alert">{copyError}</p>}
      {created && <section className="created-link" aria-label="Link criado"><div><span className="action-icon"><Check size={20} /></span><div><h2>Link pronto para {created.studentName.split(" ")[0]}</h2><p>Copie para enviar por onde preferir ou abra uma conversa no WhatsApp.</p></div><button className="btn sm ghost" aria-label="Fechar aviso" onClick={() => setCreated(null)}><X size={16} /></button></div><input className="input" aria-label="Link do formulário" readOnly value={payLink(created.id)} onFocus={(e) => e.target.select()} /><div className="share-actions"><button className="btn gold" onClick={() => copy(created)}><Copy size={16} />{copied === created.id ? "Copiado" : "Copiar link"}</button><a className="btn" href={whatsapp(created)} target="_blank" rel="noreferrer"><Send size={16} /> WhatsApp</a><Link className="btn ghost" to={`/pagar/${created.id}`} target="_blank"><ExternalLink size={16} /> Ver formulário</Link></div></section>}
      <div className="charges-toolbar">
      <div className="seg-row">
        {(["todas", "atrasado", "pendente", "pago"] as const).map((key) => (
          <button key={key} className={filter === key ? "on" : ""} onClick={() => setFilter(key)}>
            {filter === key && <motion.span layoutId="charge-filter" className="seg-on" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
            <span>{key === "todas" ? "Todas" : STATUS_LABEL[key] + "s"} <i className="num">{counts[key]}</i></span>
          </button>
        ))}
      </div>
      <label className="search"><Search size={17} /><input aria-label="Buscar cobrança por aluno" placeholder="Buscar aluno…" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
      </div>
      <section className="panel table">
        <div className="tr th"><span>Aluno</span><span>Referência</span><span>Vencimento</span><span>Valor</span><span>Situação</span><span /></div>
        <AnimatePresence initial={false}>
          {list.map((charge) => {
            const status = chargeStatus(charge);
            return (
              <motion.div className={`tr ${fresh === charge.id ? "fresh" : ""}`} key={charge.id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                <span className="who"><span className="avatar">{initials(charge.studentName)}</span><span className="grow"><b>{charge.studentName}</b><i>{plan(charge.planId).name}</i></span></span>
                <span className="muted cap">{charge.reference}</span>
                <span className="muted num">{dateBr(charge.dueDate)}</span>
                <span className="num strong">{brl(charge.cents)}</span>
                <span className="state">
                  <span className={`pill ${STATUS_TONE[status]}`}>{STATUS_LABEL[status]}</span>
                  {charge.paidAt ? <i>{charge.method === "pix" ? "Pix" : "Cartão"} · {charge.gatewayId}</i> : <i>{charge.linkSentAt ? `Link enviado ${dateBr(charge.linkSentAt).slice(0, 5)}` : "Link não enviado"}</i>}
                </span>
                <span className="acts">
                  {charge.paidAt ? (
                    <button className="btn sm ghost" title="Desfazer pagamento" onClick={() => undoPaid(charge.id)}><Undo2 size={15} /></button>
                  ) : (
                    <>
                      <a className="btn sm" href={whatsapp(charge)} target="_blank" rel="noreferrer" onClick={() => markSent(charge.id)}><Send size={14} /> Enviar</a>
                      <button className="btn sm ghost" title="Copiar link" onClick={() => copy(charge)}>{copied === charge.id ? <Check size={15} /> : <Copy size={15} />}</button>
                      <Link className="btn sm ghost" title="Abrir a tela do aluno" to={`/pagar/${charge.id}`} target="_blank"><ExternalLink size={15} /></Link>
                      <button className="btn sm ghost" title="Dar baixa manual (dinheiro)" onClick={() => markPaid(charge.id, "pix", "MANUAL")}><Check size={15} /></button>
                    </>
                  )}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {!list.length && <p className="empty">Nenhuma cobrança nesta situação.</p>}
      </section>
      <p className="list-count">{list.length} cobrança(s) encontrada(s)</p>
      <AnimatePresence>{creating && <NewCharge onClose={(result) => { setCreating(false); setParams({}, { replace: true }); if (result) { setCreated(result); setQuery(""); setFilter("todas"); setFresh(result.id); setTimeout(() => setFresh(""), 2600); } }} />}</AnimatePresence>
    </Page>
  );
}

export function Agenda() {
  const db = useDb();
  const [day, setDay] = useState(today());
  const [picking, setPicking] = useState<{ time: string; trainer: Session["trainer"] } | null>(null);
  const [open, setOpen] = useState("");
  const [error, setError] = useState("");
  const move = (days: number) => { const d = new Date(day + "T12:00:00"); d.setDate(d.getDate() + days); setDay(d.toISOString().slice(0, 10)); setPicking(null); setOpen(""); };
  const sessions = db.sessions.filter((s) => s.day === day);
  const label = new Date(day + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  return (
    <Page kicker={`${sessions.length} de ${TIMES.length * TRAINERS.length} vagas ocupadas`} title="Agenda"
      action={<div className="day-nav"><button className="btn sm" aria-label="Dia anterior" onClick={() => move(-1)}><ChevronLeft size={16} /></button><span className="cap">{day === today() ? "Hoje · " : ""}{label}</span><button className="btn sm" aria-label="Próximo dia" onClick={() => move(1)}><ChevronRight size={16} /></button></div>}>
      {error && <p className="alert" role="alert">{error}</p>}
      <section className="panel agenda">
        <div className="ag-row head"><span>Horário</span>{TRAINERS.map((t) => <span key={t}>{t}</span>)}</div>
        {TIMES.map((time, index) => (
          <motion.div className="ag-row" key={`${day}-${time}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.02, duration: 0.35, ease: EASE }}>
            <span className="num time">{time}</span>
            {TRAINERS.map((trainer) => {
              const session = sessions.find((s) => s.time === time && s.trainer === trainer);
              const choosing = picking?.time === time && picking.trainer === trainer;
              if (session) {
                return (
                  <div key={trainer} className={`cell booked ${session.status}`}>
                    <button className="cell-main" onClick={() => setOpen(open === session.id ? "" : session.id)}>
                      <span className="avatar">{initials(session.studentName)}</span><b>{session.studentName}</b>
                      <span className={`pill ${session.status === "concluido" ? "ok" : session.status === "falta" ? "danger" : "gold"}`}>{session.status === "concluido" ? "Concluído" : session.status === "falta" ? "Falta" : "Agendado"}</span>
                    </button>
                    <AnimatePresence>{open === session.id && (
                      <motion.div className="cell-menu" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                        <button onClick={() => { setSessionStatus(session.id, "concluido"); setOpen(""); }}>Concluído</button>
                        <button onClick={() => { setSessionStatus(session.id, "falta"); setOpen(""); }}>Falta</button>
                        <button onClick={() => { setSessionStatus(session.id, "agendado"); setOpen(""); }}>Agendado</button>
                        <button className="danger" onClick={() => { setSessionStatus(session.id, "remover"); setOpen(""); }}>Desmarcar</button>
                      </motion.div>
                    )}</AnimatePresence>
                  </div>
                );
              }
              return choosing ? (
                <select key={trainer} className="input cell-pick" autoFocus defaultValue="" onBlur={() => setPicking(null)}
                  onChange={(e) => { const problem = addSession({ day, time, trainer, studentName: e.target.value, status: "agendado" }); setError(problem ?? ""); setPicking(null); }}>
                  <option value="" disabled>Escolha o aluno…</option>
                  {db.students.filter((s) => !sessions.some((x) => x.time === time && x.studentName === s.name)).map((s) => <option key={s.id}>{s.name}</option>)}
                </select>
              ) : (
                <button key={trainer} className="cell free" onClick={() => { setPicking({ time, trainer }); setOpen(""); }}><Plus size={14} /> <span>Agendar</span><i>Livre</i></button>
              );
            })}
          </motion.div>
        ))}
      </section>
    </Page>
  );
}

export function Students() {
  const db = useDb();
  const [query, setQuery] = useState("");
  const key = query.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const list = db.students.filter((s) => s.name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").includes(key));
  return (
    <Page kicker={`${db.students.length} alunos ativos`} title="Alunos"
      action={<label className="search"><Search size={16} /><input placeholder="Pesquisar pelo nome…" value={query} onChange={(e) => setQuery(e.target.value)} /></label>}>
      <div className="people">
        <AnimatePresence mode="popLayout">
          {list.map((student) => {
            const latest = db.charges.filter((c) => c.studentId === student.id).sort((a, b) => b.dueDate.localeCompare(a.dueDate))[0];
            const status = latest ? chargeStatus(latest) : null;
            return (
              <motion.article className="person" key={student.id} layout initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.3, ease: EASE }}>
                <div className="person-top"><span className="avatar lg">{initials(student.name)}</span>{status && <span className={`pill ${STATUS_TONE[status]}`}>{STATUS_LABEL[status]}</span>}</div>
                <h3>{student.name}</h3>
                <p className="muted">{plan(student.planId).name} · com {student.trainer}</p>
                <dl>
                  <div><dt>WhatsApp</dt><dd className="num">{maskPhone(student.phone)}</dd></div>
                  <div><dt>Aluno desde</dt><dd className="num">{dateBr(student.since)}</dd></div>
                </dl>
              </motion.article>
            );
          })}
        </AnimatePresence>
      </div>
      {!list.length && <p className="empty">Nenhum aluno com esse nome.</p>}
    </Page>
  );
}
