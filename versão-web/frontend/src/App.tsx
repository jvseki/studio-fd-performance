import { motion } from "motion/react";
import { CalendarDays, House, LayoutGrid, Users, Wallet } from "lucide-react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { AvisoProvider } from "./componentes/ui";
import { SeletorTema } from "./lib/tema";
import { useDados } from "./lib/dados";
import { SessaoProvider, useSessao } from "./lib/sessao";
import Entrar from "./paginas/Entrar";
import Agenda from "./paginas/Agenda";
import Alunos from "./paginas/Alunos";
import Caixa from "./paginas/Caixa";
import Inicio from "./paginas/Inicio";
import Mais from "./paginas/Mais";
import Mensalidades from "./paginas/Mensalidades";

const MENU = [
  { para: "/", nome: "Início", Icone: House },
  { para: "/agenda", nome: "Agenda", Icone: CalendarDays },
  { para: "/alunos", nome: "Alunos", Icone: Users },
  { para: "/mensalidades", nome: "Mensalidades", Icone: Wallet, curto: "Pagam." },
  { para: "/mais", nome: "Mais", Icone: LayoutGrid },
];

export default function App() {
  return <SessaoProvider><Portao /></SessaoProvider>;
}

/** Só mostra o sistema depois do login. */
function Portao() {
  const { usuario } = useSessao();
  if (usuario === undefined) return <div className="carregando-tela"><span className="marca-fd">FD</span></div>;
  if (usuario === null) return <AvisoProvider><Entrar /></AvisoProvider>;
  return <Sistema />;
}

function Sistema() {
  const { pathname } = useLocation();
  const demo = useDados<{ demo: boolean }>("/saude").dados?.demo;
  const ativo = (para: string) => (para === "/" ? pathname === "/" : pathname.startsWith(para));
  return (
    <AvisoProvider>
      <div className="app">
        <aside className="lateral">
          <div className="marca"><span className="marca-fd">FD</span><span>Studio FD<i>PERFORMANCE</i></span></div>
          {MENU.map(({ para, nome, Icone }) => (
            <NavLink key={para} to={para} end={para === "/"} className={ativo(para) ? "ativa" : ""}><Icone size={19} /> {nome}</NavLink>
          ))}
          <NavLink to="/caixa" className={ativo("/caixa") ? "ativa" : ""}><Wallet size={19} /> Caixa</NavLink>
          <div style={{ marginTop: "auto" }}><SeletorTema /></div>
          <p className="rodape" style={{ marginTop: 8 }}>Versão web 1.0</p>
        </aside>
        <main className="conteudo">
          {demo && (
            <p className="faixa-demo">Demonstração com dados fictícios · os testes voltam ao início quando o servidor reinicia</p>
          )}
          <motion.div key={pathname.split("/")[1]} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <Routes>
              <Route path="/" element={<Inicio />} />
              <Route path="/agenda" element={<Agenda />} />
              <Route path="/alunos" element={<Alunos />} />
              <Route path="/mensalidades" element={<Mensalidades />} />
              <Route path="/caixa" element={<Caixa />} />
              <Route path="/mais/*" element={<Mais />} />
              <Route path="*" element={<Inicio />} />
            </Routes>
          </motion.div>
        </main>
        <nav className="abas" aria-label="Menu principal">
          {MENU.map(({ para, nome, Icone, curto }) => (
            <NavLink key={para} to={para} end={para === "/"} className={`aba ${ativo(para) ? "ativa" : ""}`}>
              {ativo(para) && <motion.span layoutId="aba-fundo" className="aba-fundo" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
              <Icone /> {curto ?? nome}
            </NavLink>
          ))}
        </nav>
      </div>
    </AvisoProvider>
  );
}
