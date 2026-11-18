import { FileText, MessageCircle, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Avatar, Campo, Carregando, Chips, Entrada, Folha, Topo, Vazio, useAviso } from "../componentes/ui";
import { api, type Aluno, type Configuracoes, type Ficha, type Plano } from "../lib/api";
import { useDados } from "../lib/dados";
import { brl, dataBr, mascaraTelefone, paraCentavos, reais, telefone } from "../lib/formato";

type Filtro = "ativos" | "todos" | "inativos";
const vazio = { full_name: "", phone: "", plan_id: "", fee: "", due_day: "", trainer_id: "", notes: "", active: true };

export default function Alunos() {
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<Filtro>("ativos");
  const ativo = filtro === "ativos" ? "&ativo=true" : filtro === "inativos" ? "&ativo=false" : "";
  const { dados, erro, recarregar } = useDados<Aluno[]>(`/alunos?q=${encodeURIComponent(busca)}${ativo}`);
  const planos = useDados<Plano[]>("/planos").dados ?? [];
  const personais = useDados<Configuracoes>("/configuracoes").dados?.personais ?? [];
  const [fichaId, setFichaId] = useState<number | null>(null);
  const ficha = useDados<Ficha>(fichaId ? `/alunos/${fichaId}` : null);
  const [editando, setEditando] = useState<number | "novo" | null>(null);
  const [form, setForm] = useState(vazio);
  const [erroForm, setErroForm] = useState("");
  const arquivo = useRef<HTMLInputElement>(null);
  const avisar = useAviso();

  const abrirForm = (aluno?: Aluno) => {
    setErroForm("");
    setEditando(aluno ? aluno.id : "novo");
    setForm(aluno ? { full_name: aluno.full_name, phone: mascaraTelefone(aluno.phone.replace(/^55/, "")), plan_id: String(aluno.plan_id ?? ""),
      fee: reais(aluno.monthly_fee_cents), due_day: String(aluno.due_day ?? ""), trainer_id: String(aluno.trainer_id ?? ""), notes: aluno.notes ?? "", active: aluno.active } : vazio);
  };
  const salvar = async () => {
    const corpo = { full_name: form.full_name, phone: form.phone, active: form.active, notes: form.notes || null,
      plan_id: form.plan_id ? Number(form.plan_id) : null, monthly_fee_cents: form.fee ? paraCentavos(form.fee) : null,
      due_day: form.due_day ? Number(form.due_day) : null, trainer_id: form.trainer_id ? Number(form.trainer_id) : null };
    try {
      const salvo = editando === "novo" ? await api.post<Aluno>("/alunos", corpo) : await api.put<Aluno>(`/alunos/${editando}`, corpo);
      avisar(editando === "novo" ? "Aluno cadastrado" : "Ficha atualizada");
      setEditando(null); recarregar();
      if (fichaId === salvo.id) ficha.recarregar();
    } catch (e) { setErroForm((e as Error).message); }
  };
  const anexar = async (lista: FileList | null) => {
    if (!lista?.[0] || !fichaId) return;
    const dados = new FormData();
    dados.append("arquivo", lista[0]);
    try { await api.form(`/alunos/${fichaId}/anamneses`, dados); avisar("Anamnese anexada"); ficha.recarregar(); }
    catch (e) { avisar((e as Error).message, true); }
    if (arquivo.current) arquivo.current.value = "";
  };
  const removerAnamnese = async (id: number) => {
    if (!confirm("Remover esta anamnese da ficha? O PDF vai para a pasta de removidos.")) return;
    await api.del(`/anamneses/${id}`); avisar("Anamnese removida"); ficha.recarregar();
  };
  const f = ficha.dados;

  return (
    <>
      <Topo sobre={dados ? `${dados.length} aluno(s)` : "Cadastro"} titulo="Alunos"
        acao={<button className="botao ouro so-grande" onClick={() => abrirForm()}><Plus /> Novo aluno</button>} />
      <label className="busca"><Search size={20} /><input placeholder="Pesquisar pelo nome…" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Pesquisar aluno" /></label>
      <Chips id="filtro-alunos" valor={filtro} aoMudar={setFiltro} opcoes={[["ativos", "Ativos"], ["todos", "Todos"], ["inativos", "Inativos"]]} />
      {erro && <p className="erro">{erro}</p>}
      {!dados ? <Carregando /> : dados.length ? (
        <div className="lista tem-flutuante">
          {dados.map((aluno, i) => (
            <Entrada key={aluno.id} indice={i}>
              <button className="cartao item" onClick={() => setFichaId(aluno.id)}>
                <Avatar nome={aluno.full_name} />
                <span className="meio"><b>{aluno.full_name}</b><span>{aluno.plan_name ?? "Sem plano"}{aluno.trainer_name ? ` · ${aluno.trainer_name}` : ""}</span></span>
                <span className="direita"><b className="num">{brl(aluno.monthly_fee_cents)}</b>{!aluno.active && <span className="selo">Inativo</span>}</span>
              </button>
            </Entrada>
          ))}
        </div>
      ) : <Vazio>{busca ? "Nenhum aluno com esse nome." : "Nenhum aluno cadastrado ainda."}</Vazio>}
      <button className="botao ouro flutuante" aria-label="Novo aluno" onClick={() => abrirForm()}><Plus /></button>

      <Folha aberta={fichaId !== null} titulo={f?.aluno.full_name ?? "Ficha"} aoFechar={() => setFichaId(null)}>
        {!f ? <Carregando linhas={3} /> : (
          <div className="campos">
            <div className="duas">
              <button className="botao" onClick={() => abrirForm(f.aluno)}><Pencil /> Editar</button>
              <a className="botao" href={`https://wa.me/${f.aluno.phone}`} target="_blank" rel="noreferrer"><MessageCircle /> WhatsApp</a>
            </div>
            <dl className="cartao recheio dados" style={{ margin: 0 }}>
              <div><dt>Plano</dt><dd>{f.aluno.plan_name ?? "Sem plano"}</dd></div>
              <div><dt>Mensalidade</dt><dd className="num">{brl(f.aluno.monthly_fee_cents)}</dd></div>
              <div><dt>Vencimento</dt><dd>{f.aluno.due_day ? `Dia ${f.aluno.due_day}` : "—"}</dd></div>
              <div><dt>Personal</dt><dd>{f.aluno.trainer_name ?? "—"}</dd></div>
              <div><dt>Telefone</dt><dd className="num">{telefone(f.aluno.phone)}</dd></div>
              <div><dt>Situação</dt><dd>{f.aluno.active ? "Ativo" : "Inativo"}</dd></div>
            </dl>
            {f.horarios_fixos.length > 0 && <p className="fraco"><b>Horários:</b> {f.horarios_fixos.join(" · ")}</p>}
            <div>
              <div className="secao-topo"><h2>Mensalidades</h2></div>
              {f.mensalidades.length ? <div className="lista">{f.mensalidades.slice(0, 4).map((m) => (
                <div key={m.id} className="cartao item" style={{ minHeight: 56 }}>
                  <span className="meio"><b className="cap">{new Date(m.reference_month + "T12:00").toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</b><span>vence {dataBr(m.due_date)}</span></span>
                  <span className="direita"><b className="num">{brl(m.amount_cents)}</b><span className={`selo ${m.status === "Pago" ? "ok" : m.status === "Atrasado" ? "perigo" : "ouro"}`}>{m.status}</span></span>
                </div>))}</div> : <p className="mais-fraco pequeno">Nenhuma mensalidade lançada.</p>}
            </div>
            <div>
              <div className="secao-topo"><h2>Anamneses</h2>
                <button className="botao mini" onClick={() => arquivo.current?.click()}><Upload size={16} /> Anexar PDF</button>
                <input ref={arquivo} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => anexar(e.target.files)} />
              </div>
              {f.anamneses.length ? <div className="lista">{f.anamneses.map((a) => (
                <div key={a.id} className="cartao item" style={{ minHeight: 56 }}>
                  <FileText size={22} color="var(--ouro-texto)" />
                  <a className="meio" href={`/api/anamneses/${a.id}/arquivo?student_id=${f.aluno.id}`} target="_blank" rel="noreferrer"><b>{a.original_name}</b><span>{dataBr(a.attached_on)}{a.notes ? ` · ${a.notes}` : ""}</span></a>
                  <button className="botao redondo leve" aria-label="Remover anamnese" onClick={() => removerAnamnese(a.id)}><Trash2 size={18} /></button>
                </div>))}</div> : <p className="mais-fraco pequeno">Nenhuma anamnese anexada.</p>}
            </div>
          </div>
        )}
      </Folha>

      <Folha aberta={editando !== null} titulo={editando === "novo" ? "Novo aluno" : "Editar aluno"} aoFechar={() => setEditando(null)}>
        <div className="campos">
          <Campo rotulo="Nome completo"><input className="entrada" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoComplete="off" /></Campo>
          <Campo rotulo="WhatsApp"><input className="entrada num" inputMode="tel" placeholder="(18) 99999-9999" value={form.phone} onChange={(e) => setForm({ ...form, phone: mascaraTelefone(e.target.value) })} /></Campo>
          <Campo rotulo="Plano">
            <select className="entrada" value={form.plan_id} onChange={(e) => {
              const p = planos.find((x) => x.id === Number(e.target.value));
              setForm({ ...form, plan_id: e.target.value, fee: p ? reais(p.price_cents) : form.fee });
            }}>
              <option value="">Sem plano</option>
              {planos.filter((p) => p.active || p.id === Number(form.plan_id)).map((p) => <option key={p.id} value={p.id}>{p.name} — {brl(p.price_cents)}</option>)}
            </select>
          </Campo>
          <div className="duas">
            <Campo rotulo="Mensalidade (R$)"><input className="entrada num" inputMode="decimal" placeholder="450,00" value={form.fee} onChange={(e) => setForm({ ...form, fee: e.target.value })} /></Campo>
            <Campo rotulo="Vencimento (dia)"><input className="entrada num" inputMode="numeric" placeholder="10" value={form.due_day} onChange={(e) => setForm({ ...form, due_day: e.target.value.replace(/\D/g, "").slice(0, 2) })} /></Campo>
          </div>
          <Campo rotulo="Personal responsável">
            <select className="entrada" value={form.trainer_id} onChange={(e) => setForm({ ...form, trainer_id: e.target.value })}>
              <option value="">Sem personal definido</option>
              {personais.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Campo>
          <Campo rotulo="Observações"><textarea className="entrada" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Campo>
          {editando !== "novo" && (
            <div className="opcoes"><button className={`opcao ${form.active ? "ativa" : ""}`} onClick={() => setForm({ ...form, active: !form.active })}>
              Aluno ativo <span className={`selo ${form.active ? "ok" : ""}`}>{form.active ? "Sim" : "Não"}</span></button></div>
          )}
          {erroForm && <p className="erro">{erroForm}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" onClick={salvar}>Salvar</button></div>
      </Folha>
    </>
  );
}
