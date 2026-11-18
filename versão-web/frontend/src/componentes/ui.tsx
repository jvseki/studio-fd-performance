import { AnimatePresence, motion } from "motion/react";
import { CircleAlert, CircleCheck, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { iniciais } from "../lib/formato";

export const EASE = [0.22, 1, 0.36, 1] as const;

// ---------------------------------------------------------------- aviso rápido
type Aviso = { texto: string; ruim?: boolean; id: number };
const AvisoCtx = createContext<(texto: string, ruim?: boolean) => void>(() => {});
export const useAviso = () => useContext(AvisoCtx);

export function AvisoProvider({ children }: { children: ReactNode }) {
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const mostrar = useCallback((texto: string, ruim = false) => setAviso({ texto, ruim, id: Date.now() }), []);
  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), 3000);
    return () => clearTimeout(t);
  }, [aviso]);
  return (
    <AvisoCtx.Provider value={mostrar}>
      {children}
      <AnimatePresence>
        {aviso && (
          <motion.div key={aviso.id} role="status" className={`aviso ${aviso.ruim ? "ruim" : ""}`}
            initial={{ opacity: 0, y: 20, x: "-50%" }} animate={{ opacity: 1, y: 0, x: "-50%" }} exit={{ opacity: 0, y: 10, x: "-50%" }} transition={{ duration: 0.3, ease: EASE }}>
            {aviso.ruim ? <CircleAlert size={20} /> : <CircleCheck size={20} />} {aviso.texto}
          </motion.div>
        )}
      </AnimatePresence>
    </AvisoCtx.Provider>
  );
}

// ---------------------------------------------------------------- folha que sobe de baixo
export function Folha({ aberta, titulo, aoFechar, children }: { aberta: boolean; titulo: string; aoFechar: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!aberta) return;
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") aoFechar(); };
    document.addEventListener("keydown", tecla);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", tecla); document.body.style.overflow = ""; };
  }, [aberta, aoFechar]);
  return (
    <AnimatePresence>
      {aberta && (
        <motion.div className="folha-fundo" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={aoFechar}>
          <motion.div className="folha" role="dialog" aria-modal="true" aria-label={titulo} onClick={(e) => e.stopPropagation()}
            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ duration: 0.42, ease: EASE }}
            drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_e, info) => { if (info.offset.y > 120 || info.velocity.y > 600) aoFechar(); }}>
            <div className="folha-pegador" />
            <div className="folha-topo">
              <h2>{titulo}</h2>
              <button className="botao redondo leve" aria-label="Fechar" onClick={aoFechar}><X /></button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------- pequenos
export const Avatar = ({ nome }: { nome: string }) => <span className="avatar" aria-hidden="true">{iniciais(nome)}</span>;

export function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return <label className="campo"><span>{rotulo}</span>{children}</label>;
}

export function Topo({ sobre, titulo, acao }: { sobre: string; titulo: string; acao?: ReactNode }) {
  return (
    <header className="topo">
      <div><p className="sobre cap">{sobre}</p><h1 className="titulo">{titulo}</h1></div>
      {acao}
    </header>
  );
}

export function Carregando({ linhas = 4 }: { linhas?: number }) {
  return <div className="lista">{Array.from({ length: linhas }, (_, i) => <div key={i} className="carregando" />)}</div>;
}

export const Vazio = ({ children }: { children: ReactNode }) => <div className="cartao vazio">{children}</div>;

export function Chips<T extends string>({ opcoes, valor, aoMudar, id }: { opcoes: [T, string][]; valor: T; aoMudar: (v: T) => void; id: string }) {
  return (
    <div className="chips" role="tablist">
      {opcoes.map(([chave, texto]) => (
        <button key={chave} role="tab" aria-selected={valor === chave} className={`chip ${valor === chave ? "ativo" : ""}`} onClick={() => aoMudar(chave)}>
          {valor === chave && <motion.span layoutId={id} className="chip-fundo" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
          <span>{texto}</span>
        </button>
      ))}
    </div>
  );
}

/** Lista que entra em cascata suave. */
export const Entrada = ({ indice, children }: { indice: number; children: ReactNode }) => (
  <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: Math.min(indice, 10) * 0.035, ease: EASE }}>
    {children}
  </motion.div>
);
