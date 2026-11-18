import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export type Tema = "auto" | "claro" | "escuro";
const CHAVE = "studiofd.tema";

function ler(): Tema {
  try {
    const salvo = localStorage.getItem(CHAVE);
    return salvo === "claro" || salvo === "escuro" ? salvo : "auto";
  } catch {
    return "auto"; // navegador sem armazenamento: segue o aparelho
  }
}

/** Aplica o tema na página (antes de desenhar, para não piscar). */
export function aplicarTema(tema: Tema = ler()) {
  const raiz = document.documentElement;
  if (tema === "auto") delete raiz.dataset.tema;
  else raiz.dataset.tema = tema;
  const escuro = tema === "escuro" || (tema === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", escuro ? "#0e0e10" : "#0b0b0c");
}

export function SeletorTema() {
  const [tema, setTema] = useState<Tema>(ler);
  useEffect(() => {
    aplicarTema(tema);
    try { localStorage.setItem(CHAVE, tema); } catch { /* sem armazenamento: vale só nesta visita */ }
  }, [tema]);
  const opcoes: [Tema, string, typeof Sun][] = [["auto", "Auto", Monitor], ["claro", "Claro", Sun], ["escuro", "Escuro", Moon]];
  return (
    <div className="tema" role="group" aria-label="Tema">
      {opcoes.map(([valor, texto, Icone]) => (
        <button key={valor} aria-pressed={tema === valor} onClick={() => setTema(valor)}><Icone size={15} /> {texto}</button>
      ))}
    </div>
  );
}
