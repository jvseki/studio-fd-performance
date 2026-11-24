import { BarChart3, ChevronRight, Clock, DatabaseBackup, KeyRound, Layers, LogOut, ShieldCheck, UserRound, Users, Wallet } from "lucide-react";
import { useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import { Campo, Carregando, Entrada, Folha, Topo, useAviso } from "../componentes/ui";
import { api, type Configuracoes, type Plano, type Usuario } from "../lib/api";
import { useSessao } from "../lib/sessao";
import { useDados } from "../lib/dados";
import { brl, hojeIso, mesLongo, paraCentavos, reais } from "../lib/formato";
import { SeletorTema } from "../lib/tema";
import { SecaoPwa } from "../lib/instalar";

const ITENS = [
  { para: "/caixa", nome: "Caixa", texto: "Entradas, saídas e saldo", Icone: Wallet },
  { para: "/mais/planos", nome: "Planos", texto: "Frequência e valores", Icone: Layers },
  { para: "/mais/relatorios", nome: "Relatórios", texto: "Resultado do mês", Icone: BarChart3 },
  { para: "/mais/configuracoes", nome: "Personais e horário", texto: "Vagas da agenda", Icone: Users },
  { para: "/mais/backup", nome: "Backup", texto: "Baixar cópia de tudo", Icone: DatabaseBackup },
  { para: "/mais/conta", nome: "Minha conta", texto: "Trocar senha e sair", Icone: UserRound },
];

function Menu() {
  const { usuario } = useSessao();
  const itens = usuario?.papel === "admin" ? [...ITENS, { para: "/mais/usuarios", nome: "Usuários", texto: "Quem acessa o sistema", Icone: ShieldCheck }] : ITENS;
  return (
    <>
      <Topo sobre="Studio FD Performance" titulo="Mais" />
      <SecaoPwa />
      <section style={{ marginBottom: 16 }}>
        <p className="pequeno fraco" style={{ fontWeight: 800, marginBottom: 8 }}>Aparência</p>
        <SeletorTema />
      </section>
      <div className="lista">
        {itens.map(({ para, nome, texto, Icone }, i) => (
          <Entrada key={para} indice={i}>
            <Link to={para} className="cartao item">
              <span className="avatar"><Icone size={20} /></span>
              <span className="meio"><b>{nome}</b><span>{texto}</span></span>
              <ChevronRight color="var(--texto-3)" />
            </Link>
          </Entrada>
        ))}
      </div>
    </>
  );
}

function Planos() {
  const { dados, recarregar } = useDados<Plano[]>("/planos");
  const [editando, setEditando] = useState<Plano | "novo" | null>(null);
  const [form, setForm] = useState({ nome: "", vezes: "3", valor: "", ativo: true });
  const [erro, setErro] = useState("");
  const avisar = useAviso();
  const abrir = (p?: Plano) => { setErro(""); setEditando(p ?? "novo"); setForm(p ? { nome: p.name, vezes: String(p.workouts_per_week), valor: reais(p.price_cents), ativo: p.active } : { nome: "", vezes: "3", valor: "", ativo: true }); };
  const salvar = async () => {
    const corpo = { name: form.nome, workouts_per_week: Number(form.vezes), price_cents: paraCentavos(form.valor), duration_months: 1, active: form.ativo };
    try {
      if (editando === "novo") await api.post("/planos", corpo); else await api.put(`/planos/${(editando as Plano).id}`, corpo);
      avisar("Plano salvo"); setEditando(null); recarregar();
    } catch (e) { setErro((e as Error).message); }
  };
  return (
    <>
      <Topo sobre="Cadastros" titulo="Planos" acao={<button className="botao ouro" onClick={() => abrir()}>Novo plano</button>} />
      {!dados ? <Carregando /> : (
        <div className="lista">
          {dados.map((p, i) => (
            <Entrada key={p.id} indice={i}>
              <button className="cartao item" onClick={() => abrir(p)}>
                <span className="avatar serif" style={{ fontSize: 20 }}>{p.workouts_per_week}x</span>
                <span className="meio"><b>{p.name}</b><span>{p.workouts_per_week} treino(s) por semana</span></span>
                <span className="direita"><b className="num">{brl(p.price_cents)}</b>{!p.active && <span className="selo">Inativo</span>}</span>
              </button>
            </Entrada>
          ))}
        </div>
      )}
      <Folha aberta={editando !== null} titulo={editando === "novo" ? "Novo plano" : "Editar plano"} aoFechar={() => setEditando(null)}>
        <div className="campos">
          <Campo rotulo="Nome"><input className="entrada" placeholder="Ex.: Individual 3x" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></Campo>
          <div className="duas">
            <Campo rotulo="Treinos por semana"><select className="entrada" value={form.vezes} onChange={(e) => setForm({ ...form, vezes: e.target.value })}>{[1, 2, 3, 4, 5, 6, 7].map((n) => <option key={n}>{n}</option>)}</select></Campo>
            <Campo rotulo="Valor (R$)"><input className="entrada num" inputMode="decimal" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} /></Campo>
          </div>
          <div className="opcoes"><button className={`opcao ${form.ativo ? "ativa" : ""}`} onClick={() => setForm({ ...form, ativo: !form.ativo })}>Plano ativo <span className={`selo ${form.ativo ? "ok" : ""}`}>{form.ativo ? "Sim" : "Não"}</span></button></div>
          <p className="mais-fraco pequeno">Mudar o preço não altera a mensalidade já combinada com cada aluno.</p>
          {erro && <p className="erro">{erro}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" onClick={salvar}>Salvar plano</button></div>
      </Folha>
    </>
  );
}

interface Relatorio { flows: { month: string; income_cents: number; expense_cents: number }[]; attendance: Record<string, number>; expenses_by_category: [string, number][]; new_students: number; active_students: number }

function Relatorios() {
  const mes = hojeIso().slice(0, 7);
  const { dados } = useDados<Relatorio>(`/relatorios?mes_ref=${mes}`);
  if (!dados) return <><Topo sobre={mesLongo(mes)} titulo="Relatórios" /><Carregando /></>;
  const atual = dados.flows[dados.flows.length - 1];
  const maior = Math.max(1, ...dados.flows.map((f) => Math.max(f.income_cents, f.expense_cents)));
  const feitos = dados.attendance.concluido ?? 0;
  const faltas = dados.attendance.falta ?? 0;
  return (
    <>
      <Topo sobre={mesLongo(mes)} titulo="Relatórios" />
      <div className="numeros">
        <div className="cartao numero destaque"><span>Resultado</span><strong className="num">{brl(atual.income_cents - atual.expense_cents)}</strong></div>
        <div className="cartao numero"><span>Entradas</span><strong className="num">{brl(atual.income_cents)}</strong></div>
        <div className="cartao numero"><span>Saídas</span><strong className="num">{brl(atual.expense_cents)}</strong></div>
        <div className="cartao numero"><span>Presença</span><strong className="num">{feitos + faltas ? `${Math.round((feitos * 100) / (feitos + faltas))}%` : "—"}</strong><small>{feitos} feito(s) · {faltas} falta(s)</small></div>
      </div>
      <section className="cartao recheio">
        <h2 style={{ fontSize: 17, marginBottom: 14 }}>Últimos 6 meses</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, alignItems: "end", height: 160 }}>
          {dados.flows.map((f) => (
            <div key={f.month} style={{ display: "grid", gap: 6, justifyItems: "center", height: "100%", alignContent: "end" }}>
              <div style={{ display: "flex", gap: 3, alignItems: "end", height: 130 }}>
                <span style={{ width: 12, height: `${(f.income_cents / maior) * 100}%`, minHeight: 2, background: "var(--ouro)", borderRadius: 4 }} />
                <span style={{ width: 12, height: `${(f.expense_cents / maior) * 100}%`, minHeight: 2, background: "var(--linha-forte)", borderRadius: 4 }} />
              </div>
              <span className="pequeno mais-fraco cap">{new Date(f.month + "T12:00").toLocaleDateString("pt-BR", { month: "short" }).replace(".", "")}</span>
            </div>
          ))}
        </div>
      </section>
      <p className="fraco pequeno" style={{ marginTop: 12 }}>{dados.active_students} aluno(s) ativo(s) · {dados.new_students} novo(s) no mês</p>
    </>
  );
}

function Config() {
  const { dados, recarregar } = useDados<Configuracoes>("/configuracoes");
  const [nomes, setNomes] = useState<Record<number, string>>({});
  const avisar = useAviso();
  if (!dados) return <><Topo sobre="Configurações" titulo="Personais e horário" /><Carregando /></>;
  const salvar = async (id: number, ativo: boolean) => {
    try { await api.put(`/personais/${id}`, { name: nomes[id] ?? dados.personais.find((p) => p.id === id)!.name, active: ativo }); avisar("Personal salvo"); recarregar(); }
    catch (e) { avisar((e as Error).message, true); }
  };
  return (
    <>
      <Topo sobre="Configurações" titulo="Personais e horário" />
      <p className="fraco" style={{ marginBottom: 12 }}>Cada personal ativo é uma coluna da agenda.</p>
      <div className="lista">
        {dados.personais.map((p) => (
          <div key={p.id} className="cartao recheio campos">
            <Campo rotulo="Nome"><input className="entrada" defaultValue={p.name} onChange={(e) => setNomes({ ...nomes, [p.id]: e.target.value })} /></Campo>
            <div className="duas">
              <button className="botao" onClick={() => salvar(p.id, !p.active)}>{p.active ? "Desativar" : "Ativar"}</button>
              <button className="botao ouro" onClick={() => salvar(p.id, p.active)}>Salvar</button>
            </div>
          </div>
        ))}
      </div>
      <section className="cartao recheio secao">
        <div className="secao-topo"><h2><Clock size={18} style={{ verticalAlign: -3 }} /> Funcionamento</h2></div>
        <p className="fraco">{dados.horario.open_time} às {dados.horario.close_time} · atendimentos de {dados.horario.slot_minutes} min · {dados.horarios.length} horários por dia</p>
      </section>
    </>
  );
}

function Backup() {
  return (
    <>
      <Topo sobre="Segurança" titulo="Backup" />
      <div className="cartao recheio campos">
        <p className="fraco">Um arquivo com alunos, agenda, mensalidades, caixa, contratos e anamneses. Guarde uma cópia toda semana em outro lugar (pen drive ou nuvem).</p>
        <a className="botao ouro largo" href="/api/backup" download><DatabaseBackup /> Baixar backup agora</a>
      </div>
    </>
  );
}

function Conta() {
  const { usuario, sair: encerrar } = useSessao();
  const navegar = useNavigate();
  // Ao sair, volta para o Início: quem entrar de novo começa pela tela principal.
  const sair = () => { navegar("/", { replace: true }); encerrar(); };
  const [form, setForm] = useState({ atual: "", nova: "", repetir: "" });
  const [erro, setErro] = useState("");
  const avisar = useAviso();
  const trocar = async () => {
    setErro("");
    if (form.nova !== form.repetir) { setErro("A nova senha e a repetição estão diferentes."); return; }
    try {
      await api.post("/eu/senha", { atual: form.atual, nova: form.nova });
      avisar("Senha trocada. Entre de novo com a senha nova.");
      setTimeout(() => sair(), 1200);
    } catch (e) { setErro((e as Error).message); }
  };
  return (
    <>
      <Topo sobre={usuario?.papel === "admin" ? "Administrador" : "Equipe"} titulo="Minha conta" />
      <div className="cartao recheio" style={{ marginBottom: 14 }}>
        <b>{usuario?.nome}</b>
        <p className="fraco">{usuario?.email}</p>
      </div>
      <section className="cartao recheio campos">
        <h2 style={{ fontSize: 17 }}><KeyRound size={18} style={{ verticalAlign: -3 }} /> Trocar senha</h2>
        <Campo rotulo="Senha atual"><input className="entrada" type="password" autoComplete="current-password" value={form.atual} onChange={(e) => setForm({ ...form, atual: e.target.value })} /></Campo>
        <Campo rotulo="Nova senha (8+ caracteres, letras e números)"><input className="entrada" type="password" autoComplete="new-password" value={form.nova} onChange={(e) => setForm({ ...form, nova: e.target.value })} /></Campo>
        <Campo rotulo="Repita a nova senha"><input className="entrada" type="password" autoComplete="new-password" value={form.repetir} onChange={(e) => setForm({ ...form, repetir: e.target.value })} /></Campo>
        {erro && <p className="erro">{erro}</p>}
        <button className="botao ouro largo" onClick={trocar}>Salvar nova senha</button>
      </section>
      <div className="acoes"><button className="botao largo perigo" onClick={sair}><LogOut /> Sair desta conta</button></div>
    </>
  );
}

function Usuarios() {
  const { dados, erro, recarregar } = useDados<Usuario[]>("/usuarios");
  const { usuario } = useSessao();
  const [novo, setNovo] = useState(false);
  const [form, setForm] = useState({ nome: "", email: "", senha: "", papel: "equipe" });
  const [erroForm, setErroForm] = useState("");
  const avisar = useAviso();
  const criar = async () => {
    try { await api.post("/usuarios", form); avisar(`Acesso criado para ${form.nome.split(" ")[0]}`); setNovo(false); recarregar(); }
    catch (e) { setErroForm((e as Error).message); }
  };
  const alternar = async (u: Usuario) => {
    try { await api.patch(`/usuarios/${u.id}`, { ativo: !u.ativo }); avisar(u.ativo ? "Acesso bloqueado" : "Acesso liberado"); recarregar(); }
    catch (e) { avisar((e as Error).message, true); }
  };
  const redefinir = async (u: Usuario) => {
    const nova = prompt(`Nova senha para ${u.nome} (8+ caracteres, letras e números):`);
    if (!nova) return;
    try { await api.post(`/usuarios/${u.id}/senha`, { nova }); avisar("Senha redefinida. Passe a nova senha para a pessoa."); }
    catch (e) { avisar((e as Error).message, true); }
  };
  return (
    <>
      <Topo sobre="Administração" titulo="Usuários" acao={<button className="botao ouro" onClick={() => { setNovo(true); setErroForm(""); setForm({ nome: "", email: "", senha: "", papel: "equipe" }); }}>Novo acesso</button>} />
      <p className="fraco" style={{ marginBottom: 12 }}>Crie um acesso para cada pessoa (Douglas, Fran). Não compartilhe a mesma senha.</p>
      {erro && <p className="erro">{erro}</p>}
      {!dados ? <Carregando /> : (
        <div className="lista">
          {dados.map((u, i) => (
            <Entrada key={u.id} indice={i}>
              <div className="cartao item">
                <span className="avatar">{u.nome.slice(0, 2).toUpperCase()}</span>
                <span className="meio"><b>{u.nome}</b><span>{u.email}</span></span>
                <span className="direita">
                  <span className={`selo ${u.papel === "admin" ? "ouro" : ""}`}>{u.papel === "admin" ? "Admin" : "Equipe"}</span>
                  {!u.ativo && <span className="selo perigo">Bloqueado</span>}
                </span>
              </div>
              {u.id !== usuario?.id && (
                <div className="duas" style={{ marginTop: 6 }}>
                  <button className="botao mini" onClick={() => redefinir(u)}>Nova senha</button>
                  <button className={`botao mini ${u.ativo ? "perigo" : ""}`} onClick={() => alternar(u)}>{u.ativo ? "Bloquear" : "Liberar"}</button>
                </div>
              )}
            </Entrada>
          ))}
        </div>
      )}
      <Folha aberta={novo} titulo="Novo acesso" aoFechar={() => setNovo(false)}>
        <div className="campos">
          <Campo rotulo="Nome"><input className="entrada" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></Campo>
          <Campo rotulo="E-mail"><input className="entrada" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Campo>
          <Campo rotulo="Senha inicial (8+ caracteres, letras e números)"><input className="entrada" type="text" autoComplete="off" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} /></Campo>
          <Campo rotulo="Tipo de acesso">
            <select className="entrada" value={form.papel} onChange={(e) => setForm({ ...form, papel: e.target.value })}>
              <option value="equipe">Equipe (usa o sistema)</option>
              <option value="admin">Administrador (também gerencia acessos)</option>
            </select>
          </Campo>
          {erroForm && <p className="erro">{erroForm}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" onClick={criar}>Criar acesso</button></div>
      </Folha>
    </>
  );
}

export default function Mais() {
  return (
    <Routes>
      <Route index element={<Menu />} />
      <Route path="planos" element={<Planos />} />
      <Route path="relatorios" element={<Relatorios />} />
      <Route path="configuracoes" element={<Config />} />
      <Route path="backup" element={<Backup />} />
      <Route path="conta" element={<Conta />} />
      <Route path="usuarios" element={<Usuarios />} />
    </Routes>
  );
}
