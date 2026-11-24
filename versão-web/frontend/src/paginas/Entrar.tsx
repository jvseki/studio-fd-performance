import { motion } from "motion/react";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { EASE } from "../componentes/ui";
import { useSessao } from "../lib/sessao";
import { useDados } from "../lib/dados";

export default function Entrar() {
  const { entrar } = useSessao();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [ver, setVer] = useState(false);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const demo = useDados<{ demo: boolean }>("/saude").dados?.demo;
  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErro(""); setEnviando(true);
    try { await entrar(email, senha); } catch (falha) { setErro((falha as Error).message); setEnviando(false); }
  };
  return (
    <main className="entrar">
      <motion.form className="entrar-cartao" onSubmit={enviar} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }}>
        <div className="marca entrar-marca"><span className="marca-fd">FD</span><span>Studio FD<i>PERFORMANCE</i></span></div>
        <h1 className="titulo">Bem-vindo de volta.</h1>
        <p className="fraco" style={{ margin: "6px 0 22px" }}>Entre com o e-mail e a senha da sua conta.</p>
        {demo && (
          <button type="button" className="faixa-demo" style={{ width: "100%", cursor: "pointer" }} onClick={() => { setEmail("demo@studiofd.com.br"); setSenha("studiofd2026"); }}>
            Demonstração com alunos fictícios · toque aqui para preencher<br />demo@studiofd.com.br · studiofd2026
          </button>
        )}
        <div className="campos">
          <label className="campo"><span>E-mail</span>
            <input className="entrada" type="email" name="email" autoComplete="username" inputMode="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="campo"><span>Senha</span>
            <span className="senha">
              <input className="entrada" type={ver ? "text" : "password"} name="senha" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
              <button type="button" className="botao redondo leve" aria-label={ver ? "Esconder senha" : "Mostrar senha"} onClick={() => setVer(!ver)}>{ver ? <EyeOff /> : <Eye />}</button>
            </span>
          </label>
          {erro && <p className="erro" role="alert">{erro}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" disabled={enviando}><LogIn /> {enviando ? "Entrando…" : "Entrar"}</button></div>
        <p className="mais-fraco pequeno" style={{ marginTop: 16, textAlign: "center" }}>Esqueceu a senha? Peça ao administrador para criar uma nova.</p>
      </motion.form>
    </main>
  );
}
