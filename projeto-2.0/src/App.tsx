import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

// Cada área carrega só quando é aberta: o aluno no celular não baixa o painel.
const Pay = lazy(() => import("./pages/Pay"));
const Chat = lazy(() => import("./pages/DemoChat"));
const painel = () => import("./pages/Painel");
const PainelLayout = lazy(() => painel().then((m) => ({ default: m.PainelLayout })));
const Overview = lazy(() => painel().then((m) => ({ default: m.Overview })));
const Charges = lazy(() => painel().then((m) => ({ default: m.Charges })));
const Agenda = lazy(() => painel().then((m) => ({ default: m.Agenda })));
const Students = lazy(() => painel().then((m) => ({ default: m.Students })));

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <Suspense fallback={null}>
      <ScrollTop />
      <Routes>
        <Route path="/" element={<Navigate to="/painel" replace />} />
        <Route path="/pagar/:id" element={<Pay />} />
        <Route path="/demo/conversa" element={<Chat />} />
        <Route path="/painel" element={<PainelLayout />}>
          <Route index element={<Overview />} />
          <Route path="cobrancas" element={<Charges />} />
          <Route path="agenda" element={<Agenda />} />
          <Route path="alunos" element={<Students />} />
        </Route>
        <Route path="*" element={<div className="pay"><main className="pay-box missing"><h1>Página não encontrada</h1><p>Confira o endereço recebido. Se você é aluno, peça um novo link ao Studio.</p></main></div>} />
      </Routes>
    </Suspense>
  );
}
