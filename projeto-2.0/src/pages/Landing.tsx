import { AnimatePresence, motion, useMotionValueEvent, useScroll, useSpring, useTransform } from "motion/react";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createCharge, PLANS, STUDIO, type PlanKind } from "../data/store";
import { brl } from "../lib/format";
import { EASE, Lines, Reveal, Tilt, useSmoothScroll } from "../lib/motion";
import "../styles/landing.css";

const BOARD: [string, string, string][] = [
  ["06:00", "Ana Beatriz", "Bruno"],
  ["07:00", "Carla", "Diego"],
  ["08:00", "Eduarda", ""],
  ["09:00", "Gabriela", "Isabela"],
  ["17:00", "João Pedro", "Felipe"],
];

function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const smooth = useSpring(scrollYProgress, { stiffness: 90, damping: 22 });
  const rotateX = useTransform(smooth, [0, 1], [16, 2]);
  const rotateY = useTransform(smooth, [0, 1], [-24, -4]);
  const boardY = useTransform(smooth, [0, 1], [0, 140]);
  const titleY = useTransform(smooth, [0, 1], [0, -90]);
  const fade = useTransform(smooth, [0, 0.7], [1, 0]);
  return (
    <section className="hero" ref={ref}>
      <motion.div className="hero-copy" style={{ y: titleY, opacity: fade }}>
        <motion.p className="kicker" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 1 }}>
          {STUDIO.city} — atendimento personalizado
        </motion.p>
        <h1 className="serif hero-title">
          <Lines lines={["Treino com", <>atenção <em>de verdade.</em></>]} delay={0.15} />
        </h1>
        <motion.p className="hero-sub" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.9, ease: EASE }}>
          No Studio FD Performance cada personal atende no máximo dois alunos por vez.
          Você treina acompanhado do aquecimento ao último exercício.
        </motion.p>
        <motion.div className="hero-actions" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9, duration: 0.9, ease: EASE }}>
          <a className="btn gold" href="#planos">Ver planos <ArrowRight size={16} /></a>
          <a className="btn ghost" href="#metodo">Como funciona</a>
        </motion.div>
      </motion.div>

      <div className="hero-stage" aria-hidden="true">
        <motion.div className="board" style={{ rotateX, rotateY, y: boardY }} initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.35, duration: 1.3, ease: EASE }}>
          <div className="board-head">
            <span>Agenda de hoje</span>
            <span className="faint">Douglas · Fran</span>
          </div>
          {BOARD.map(([time, first, second], index) => (
            <motion.div className="board-row" key={time} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.75 + index * 0.09, duration: 0.8, ease: EASE }}>
              <span className="board-time num">{time}</span>
              <span className="board-slot">{first}</span>
              <span className={second ? "board-slot" : "board-slot free"}>{second || "vaga livre"}</span>
            </motion.div>
          ))}
          <div className="board-foot">No máximo 2 alunos por personal</div>
        </motion.div>
        <motion.div className="board-shadow" style={{ y: boardY }} />
      </div>

      <div className="hero-facts">
        {["Máximo de 2 alunos por personal", "Ambiente climatizado", "Aparelhos novos"].map((fact, index) => (
          <motion.span key={fact} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 + index * 0.12, duration: 0.8 }}>{fact}</motion.span>
        ))}
      </div>
    </section>
  );
}

const STEPS = [
  { figure: "2", title: "alunos por personal. No máximo.", text: "Você não divide a atenção com uma turma inteira. O personal acompanha cada repetição, corrige a postura e ajusta a carga na hora." },
  { figure: "1", title: "plano de treino: o seu.", text: "Objetivo, histórico e limites de cada aluno entram na conta. Cada treino é pensado para a pessoa, não copiado de uma ficha pronta." },
  { figure: "0", title: "fila para usar aparelho.", text: "Seu horário fica reservado toda semana. Você chega, treina e vai embora, sem esperar ninguém desocupar o equipamento." },
];

function Method() {
  const ref = useRef<HTMLElement>(null);
  const [step, setStep] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (value) => setStep(Math.min(STEPS.length - 1, Math.floor(value * STEPS.length))));
  const ringRotate = useTransform(scrollYProgress, [0, 1], [0, 150]);
  const bar = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);
  const current = STEPS[step];
  return (
    <section className="method" id="metodo" ref={ref}>
      <div className="method-pin">
        <div className="method-figure">
          <motion.div className="method-ring" style={{ rotate: ringRotate }} />
          <AnimatePresence mode="popLayout">
            <motion.span key={current.figure} className="serif method-number"
              initial={{ rotateX: -80, opacity: 0, y: 60 }} animate={{ rotateX: 0, opacity: 1, y: 0 }} exit={{ rotateX: 80, opacity: 0, y: -60 }}
              transition={{ duration: 0.7, ease: EASE }}>
              {current.figure}
            </motion.span>
          </AnimatePresence>
        </div>
        <div className="method-text">
          <p className="kicker">O método</p>
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, y: 26 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -18 }} transition={{ duration: 0.45, ease: EASE }}>
              <h2 className="serif method-title">{current.title}</h2>
              <p className="method-body">{current.text}</p>
            </motion.div>
          </AnimatePresence>
          <div className="method-progress">
            <div className="method-track"><motion.div style={{ width: bar }} /></div>
            <span className="num faint">0{step + 1} / 0{STEPS.length}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

const SPACES = [
  { n: "01", title: "Climatizado o ano inteiro", text: "Treinar em Andradina no verão não precisa ser um sofrimento. O ambiente fica na temperatura certa.", art: "air" },
  { n: "02", title: "Aparelhos novos e modernos", text: "Equipamentos escolhidos para o atendimento personalizado, com manutenção em dia.", art: "weight" },
  { n: "03", title: "Acompanhamento de perto", text: "Atendimento humanizado, respeitando a individualidade e o objetivo de cada aluno.", art: "pair" },
  { n: "04", title: "Horário que é seu", text: "Você escolhe os dias e o horário. Eles ficam reservados para você toda semana.", art: "clock" },
] as const;

function Art({ kind }: { kind: (typeof SPACES)[number]["art"] }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return (
    <svg viewBox="0 0 200 200" className="space-art" aria-hidden="true">
      {kind === "air" && <g {...common}>{[40, 70, 100, 130, 160].map((y, i) => <path key={y} d={`M20 ${y} C60 ${y - 22 + i * 3} 90 ${y + 22 - i * 3} 130 ${y} S180 ${y - 16} 184 ${y}`} opacity={1 - i * 0.14} />)}</g>}
      {kind === "weight" && <g {...common}><path d="M52 100h96" /><rect x="34" y="62" width="18" height="76" rx="5" /><rect x="148" y="62" width="18" height="76" rx="5" /><rect x="18" y="78" width="16" height="44" rx="5" /><rect x="166" y="78" width="16" height="44" rx="5" /></g>}
      {kind === "pair" && <g {...common}><circle cx="70" cy="62" r="20" /><path d="M32 150c4-30 20-46 38-46s34 16 38 46" /><circle cx="134" cy="76" r="15" /><path d="M112 150c3-22 12-36 22-36 16 0 26 14 30 36" /><circle cx="100" cy="100" r="88" opacity=".25" /></g>}
      {kind === "clock" && <g {...common}><circle cx="100" cy="100" r="78" /><path d="M100 52v50l34 22" />{Array.from({ length: 12 }, (_, i) => { const a = (i * Math.PI) / 6; return <path key={i} d={`M${100 + Math.sin(a) * 66} ${100 - Math.cos(a) * 66}L${100 + Math.sin(a) * 72} ${100 - Math.cos(a) * 72}`} />; })}</g>}
    </svg>
  );
}

function Spaces() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const x = useTransform(useSpring(scrollYProgress, { stiffness: 80, damping: 20 }), [0, 1], ["2%", "-71%"]);
  return (
    <section className="spaces" id="estrutura" ref={ref}>
      <div className="spaces-pin">
        <div className="spaces-head">
          <p className="kicker">A estrutura</p>
          <h2 className="serif">Conforto para treinar <em>bem.</em></h2>
        </div>
        <motion.div className="spaces-rail" style={{ x }}>
          {SPACES.map((space) => (
            <article className="space" key={space.n}>
              <span className="serif space-n">{space.n}</span>
              <Art kind={space.art} />
              <h3 className="serif">{space.title}</h3>
              <p>{space.text}</p>
            </article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function Plans() {
  const [kind, setKind] = useState<PlanKind>("individual");
  const navigate = useNavigate();
  const start = (planId: string, cents: number) => {
    const due = new Date(); due.setDate(due.getDate() + 3);
    const charge = createCharge({ studentName: "", phone: "", planId, cents, dueDate: due.toISOString().slice(0, 10) });
    navigate(`/pagar/${charge.id}`);
  };
  const shown = PLANS.filter((item) => item.kind === kind);
  return (
    <section className="plans" id="planos">
      <Reveal className="plans-head">
        <div>
          <p className="kicker">Planos</p>
          <h2 className="serif">Escolha quantas vezes <em>por semana.</em></h2>
        </div>
        <div className="seg" role="tablist" aria-label="Tipo de plano">
          {(["individual", "casal"] as const).map((option) => (
            <button key={option} role="tab" aria-selected={kind === option} className={kind === option ? "on" : ""} onClick={() => setKind(option)}>
              {kind === option && <motion.span layoutId="seg-pill" className="seg-pill" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
              <span>{option === "individual" ? "Individual" : "Casal"}</span>
            </button>
          ))}
        </div>
      </Reveal>
      <div className={`plan-grid ${kind}`}>
        <AnimatePresence mode="popLayout">
          {shown.map((item, index) => (
            <motion.div key={item.id} layout initial={{ opacity: 0, y: 30, rotateX: -12 }} animate={{ opacity: 1, y: 0, rotateX: 0 }} exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.6, delay: index * 0.06, ease: EASE }} style={{ transformPerspective: 900 }}>
              <Tilt className="plan" max={7}>
                <div className="plan-top">
                  <span className="serif plan-times">{item.perWeek}x</span>
                  <span className="muted">na semana</span>
                </div>
                <p className="plan-desc">{item.kind === "casal" ? "Treinando juntos, no mesmo horário." : "Atendimento personalizado."}</p>
                <div className="plan-price">
                  <span className="serif num">{brl(item.cents).replace(",00", "")}</span>
                  <span className="muted">/mês{item.kind === "casal" ? " · o casal" : ""}</span>
                </div>
                <button className="btn gold block" onClick={() => start(item.id, item.cents / (item.kind === "casal" ? 2 : 1))}>Começar com este <ArrowRight size={16} /></button>
              </Tilt>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <p className="plans-note faint">Mensalidade paga por Pix ou cartão, direto pelo link do Studio.</p>
    </section>
  );
}

function Closing() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end end"] });
  const scale = useTransform(scrollYProgress, [0, 1], [0.82, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [0.2, 1]);
  return (
    <footer className="closing" ref={ref}>
      <motion.h2 className="serif" style={{ scale, opacity }}>Seu objetivo,<br /><em>nosso compromisso.</em></motion.h2>
      <a className="btn gold" href="#planos">Quero começar <ArrowUpRight size={16} /></a>
      <div className="closing-foot">
        <span>Studio FD Performance · {STUDIO.city}</span>
        <Link to="/painel">Área do Studio</Link>
      </div>
    </footer>
  );
}

export default function Landing() {
  useSmoothScroll();
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 26 });
  return (
    <div className="landing">
      <motion.div className="scroll-bar" style={{ scaleX: progress }} />
      <header className="nav">
        <a href="#topo" className="brand"><span className="brand-mark serif">FD</span><span>Studio FD <i>Performance</i></span></a>
        <nav>
          <a href="#metodo">Método</a>
          <a href="#estrutura">Estrutura</a>
          <a href="#planos">Planos</a>
        </nav>
        <Link className="btn sm" to="/painel">Área do Studio</Link>
      </header>
      <main id="topo">
        <Hero />
        <div className="marquee" aria-hidden="true">
          <div>{Array.from({ length: 2 }, (_, i) => <span key={i}>Atendimento personalizado <b>✦</b> Musculação <b>✦</b> Acompanhamento individual <b>✦</b> Andradina SP <b>✦</b> Resultado com método <b>✦</b>&nbsp;</span>)}</div>
        </div>
        <Method />
        <Spaces />
        <Plans />
      </main>
      <Closing />
    </div>
  );
}
