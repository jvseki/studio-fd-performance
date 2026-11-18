import { ArrowDownLeft, ArrowUpRight, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import { useState } from "react";
import { Campo, Carregando, Chips, Entrada, Folha, Topo, Vazio, useAviso } from "../componentes/ui";
import { api, FORMAS, type Configuracoes, type Movimento } from "../lib/api";
import { useDados } from "../lib/dados";
import { brl, dataBr, diaLongo, hojeIso, mesLongo, paraCentavos, somarDias, somarMeses } from "../lib/formato";

const ultimoDia = (mes: string) => { const [a, m] = mes.split("-").map(Number); return `${mes}-${String(new Date(a, m, 0).getDate()).padStart(2, "0")}`; };

export default function Caixa() {
  const [modo, setModo] = useState<"dia" | "mes">("dia");
  const [dia, setDia] = useState(hojeIso());
  const inicio = modo === "dia" ? dia : `${dia.slice(0, 7)}-01`;
  const fim = modo === "dia" ? dia : ultimoDia(dia.slice(0, 7));
  const { dados, erro, recarregar } = useDados<{ lista: Movimento[]; entradas: number; saidas: number; saldo: number }>(`/caixa?inicio=${inicio}&fim=${fim}`);
  const config = useDados<Configuracoes>("/configuracoes").dados;
  const [novo, setNovo] = useState<"entrada" | "saida" | null>(null);
  const [form, setForm] = useState({ descricao: "", categoria: "", valor: "", forma: "Pix" });
  const [erroForm, setErroForm] = useState("");
  const avisar = useAviso();
  const mover = (n: number) => setDia(modo === "dia" ? somarDias(dia, n) : `${somarMeses(dia.slice(0, 7), n)}-01`);

  const abrir = (tipo: "entrada" | "saida") => {
    setNovo(tipo); setErroForm("");
    setForm({ descricao: "", categoria: (tipo === "entrada" ? config?.categorias_entrada : config?.categorias_saida)?.[0] ?? "Outros", valor: "", forma: "Pix" });
  };
  const salvar = async () => {
    try {
      await api.post("/caixa", { day: modo === "dia" ? dia : hojeIso(), description: form.descricao, category: form.categoria, kind: novo, amount_cents: paraCentavos(form.valor), method: form.forma });
      avisar(novo === "entrada" ? "Entrada lançada" : "Saída lançada"); setNovo(null); recarregar();
    } catch (e) { setErroForm((e as Error).message); }
  };
  const excluir = async (m: Movimento) => {
    if (!confirm(`Excluir “${m.description}”?`)) return;
    try { await api.del(`/caixa/${m.id}`); avisar("Movimentação excluída"); recarregar(); } catch (e) { avisar((e as Error).message, true); }
  };

  return (
    <>
      <Topo sobre="Financeiro" titulo="Caixa" />
      <div className="duas" style={{ marginBottom: 14 }}>
        <button className="botao" onClick={() => abrir("entrada")}><ArrowDownLeft color="var(--ok)" /> Entrada</button>
        <button className="botao preto" onClick={() => abrir("saida")}><ArrowUpRight color="var(--ouro-claro)" /> Saída</button>
      </div>
      <Chips id="modo-caixa" valor={modo} aoMudar={setModo} opcoes={[["dia", "Dia"], ["mes", "Mês"]]} />
      <div className="navegador">
        <button className="botao redondo" aria-label="Anterior" onClick={() => mover(-1)}><ChevronLeft /></button>
        <span className="rotulo cap">{modo === "dia" ? diaLongo(dia) : mesLongo(dia)}</span>
        <button className="botao redondo" aria-label="Próximo" onClick={() => mover(1)}><ChevronRight /></button>
      </div>
      {dados && (
        <div className="numeros">
          <div className="cartao numero"><span>Entradas</span><strong className="num" style={{ color: "var(--ok)" }}>{brl(dados.entradas)}</strong></div>
          <div className="cartao numero"><span>Saídas</span><strong className="num" style={{ color: "var(--perigo)" }}>{brl(dados.saidas)}</strong></div>
          <div className="cartao numero destaque" style={{ gridColumn: "1 / -1" }}><span>Saldo</span><strong className="num">{brl(dados.saldo)}</strong></div>
        </div>
      )}
      {erro && <p className="erro">{erro}</p>}
      {!dados ? <Carregando /> : dados.lista.length ? (
        <div className="lista">
          {dados.lista.map((m, i) => (
            <Entrada key={m.id} indice={i}>
              <div className="cartao item">
                {m.kind === "entrada" ? <ArrowDownLeft color="var(--ok)" /> : <ArrowUpRight color="var(--perigo)" />}
                <span className="meio"><b>{m.description}</b><span>{m.category} · {m.method ?? "—"} · {dataBr(m.day).slice(0, 5)}</span></span>
                <b className="num" style={{ color: m.kind === "entrada" ? "var(--ok)" : "var(--perigo)" }}>{m.kind === "entrada" ? "+" : "−"} {brl(m.amount_cents)}</b>
                {!m.payment_id && <button className="botao redondo leve" aria-label="Excluir" onClick={() => excluir(m)}><Trash2 size={18} /></button>}
              </div>
            </Entrada>
          ))}
        </div>
      ) : <Vazio>Nenhuma movimentação neste período.</Vazio>}

      <Folha aberta={!!novo} titulo={novo === "entrada" ? "Nova entrada" : "Nova saída"} aoFechar={() => setNovo(null)}>
        <div className="campos">
          <Campo rotulo="Descrição"><input className="entrada" placeholder={novo === "entrada" ? "Ex.: Avaliação física" : "Ex.: Conta de energia"} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} /></Campo>
          <div className="duas">
            <Campo rotulo="Valor (R$)"><input className="entrada num" inputMode="decimal" placeholder="0,00" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} /></Campo>
            <Campo rotulo="Forma"><select className="entrada" value={form.forma} onChange={(e) => setForm({ ...form, forma: e.target.value })}>{FORMAS.map((f) => <option key={f}>{f}</option>)}</select></Campo>
          </div>
          <Campo rotulo="Categoria">
            <select className="entrada" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
              {((novo === "entrada" ? config?.categorias_entrada : config?.categorias_saida) ?? ["Outros"]).map((c) => <option key={c}>{c}</option>)}
            </select>
          </Campo>
          {erroForm && <p className="erro">{erroForm}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" onClick={salvar}>Lançar</button></div>
      </Folha>
    </>
  );
}
