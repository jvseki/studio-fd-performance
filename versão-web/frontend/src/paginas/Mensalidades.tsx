import { ChevronLeft, ChevronRight, RefreshCw, Undo2 } from "lucide-react";
import { useState } from "react";
import { Avatar, Campo, Carregando, Chips, Entrada, Folha, Topo, Vazio, useAviso } from "../componentes/ui";
import { api, FORMAS, type Mensalidade, type ResumoMes } from "../lib/api";
import { useDados } from "../lib/dados";
import { brl, dataBr, hojeIso, mesLongo, paraCentavos, reais, somarMeses } from "../lib/formato";

type Filtro = "todas" | "Atrasado" | "Pendente" | "Pago";
const TOM = { Pago: "ok", Pendente: "ouro", Atrasado: "perigo" } as const;

export default function Mensalidades() {
  const [mes, setMes] = useState(hojeIso().slice(0, 7));
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const { dados, erro, recarregar } = useDados<{ lista: Mensalidade[]; resumo: ResumoMes }>(`/mensalidades?mes_ref=${mes}`);
  const [aberta, setAberta] = useState<Mensalidade | null>(null);
  const [pag, setPag] = useState({ forma: "Pix", valor: "", data: hojeIso() });
  const [erroForm, setErroForm] = useState("");
  const avisar = useAviso();

  const gerar = async () => {
    try {
      const r = await api.post<{ geradas: number }>(`/mensalidades/gerar?mes_ref=${mes}`);
      avisar(r.geradas ? `${r.geradas} mensalidade(s) gerada(s)` : "Todos já têm mensalidade neste mês");
      recarregar();
    } catch (e) { avisar((e as Error).message, true); }
  };
  const abrir = (m: Mensalidade) => { setAberta(m); setErroForm(""); setPag({ forma: "Pix", valor: reais(m.amount_cents), data: hojeIso() }); };
  const pagar = async () => {
    if (!aberta) return;
    try {
      await api.post(`/mensalidades/${aberta.id}/pagar`, { paid_on: pag.data, method: pag.forma, amount_cents: paraCentavos(pag.valor) });
      avisar(`Pagamento de ${aberta.student_name.split(" ")[0]} registrado`); setAberta(null); recarregar();
    } catch (e) { setErroForm((e as Error).message); }
  };
  const desfazer = async () => {
    if (!aberta || !confirm("Desfazer este pagamento? A entrada sai do caixa.")) return;
    await api.post(`/mensalidades/${aberta.id}/desfazer`); avisar("Pagamento desfeito"); setAberta(null); recarregar();
  };
  const lista = dados?.lista.filter((m) => filtro === "todas" || m.status === filtro) ?? [];
  const r = dados?.resumo;

  return (
    <>
      <Topo sobre="Financeiro" titulo="Mensalidades" acao={<button className="botao ouro" onClick={gerar}><RefreshCw /> Gerar do mês</button>} />
      <div className="navegador">
        <button className="botao redondo" aria-label="Mês anterior" onClick={() => setMes(somarMeses(mes, -1))}><ChevronLeft /></button>
        <span className="rotulo cap">{mesLongo(mes)}</span>
        <button className="botao redondo" aria-label="Próximo mês" onClick={() => setMes(somarMeses(mes, 1))}><ChevronRight /></button>
      </div>
      {r && (
        <div className="numeros">
          <div className="cartao numero destaque"><span>Recebido</span><strong className="num">{brl(r.received_cents)}</strong><small>{r.paid} paga(s)</small></div>
          <div className="cartao numero"><span>Previsto</span><strong className="num">{brl(r.expected_cents)}</strong><small>{dados.lista.length} lançada(s)</small></div>
          <div className="cartao numero"><span>A receber</span><strong className="num">{brl(r.pending_cents)}</strong><small>{r.pending} no prazo</small></div>
          <div className="cartao numero"><span>Atrasado</span><strong className="num">{brl(r.overdue_cents)}</strong><small>{r.overdue} vencida(s)</small></div>
        </div>
      )}
      {r && r.missing > 0 && <p className="cartao recheio pequeno" style={{ marginBottom: 12 }}>{r.missing} aluno(s) ativo(s) ainda sem mensalidade neste mês. Toque em <b>Gerar do mês</b>.</p>}
      <Chips id="filtro-mensal" valor={filtro} aoMudar={setFiltro} opcoes={[["todas", "Todas"], ["Atrasado", "Atrasadas"], ["Pendente", "Pendentes"], ["Pago", "Pagas"]]} />
      {erro && <p className="erro">{erro}</p>}
      {!dados ? <Carregando /> : lista.length ? (
        <div className="lista">
          {lista.map((m, i) => (
            <Entrada key={m.id} indice={i}>
              <button className="cartao item" onClick={() => abrir(m)}>
                <Avatar nome={m.student_name} />
                <span className="meio"><b>{m.student_name}</b><span>{m.paid_on ? `${m.method} · ${dataBr(m.paid_on)}` : `vence ${dataBr(m.due_date)}`}</span></span>
                <span className="direita"><b className="num">{brl(m.amount_cents)}</b><span className={`selo ${TOM[m.status]}`}>{m.status}</span></span>
              </button>
            </Entrada>
          ))}
        </div>
      ) : <Vazio>Nenhuma mensalidade {filtro === "todas" ? "neste mês" : "nesta situação"}.</Vazio>}

      <Folha aberta={!!aberta} titulo={aberta?.student_name ?? ""} aoFechar={() => setAberta(null)}>
        {aberta?.paid_on ? (
          <>
            <p className="fraco">Pago em {dataBr(aberta.paid_on)} por {aberta.method} · {brl(aberta.amount_cents)}</p>
            <div className="acoes"><button className="botao largo perigo" onClick={desfazer}><Undo2 /> Desfazer pagamento</button></div>
          </>
        ) : aberta && (
          <>
            <div className="campos">
              <p className="fraco">Vencimento {dataBr(aberta.due_date)}. O valor entra no caixa automaticamente.</p>
              <Campo rotulo="Forma de pagamento">
                <div className="chips" style={{ flexWrap: "wrap" }}>{FORMAS.map((f) => <button key={f} className={`chip ${pag.forma === f ? "ativo" : ""}`} style={pag.forma === f ? { background: "var(--preto)" } : undefined} onClick={() => setPag({ ...pag, forma: f })}><span>{f}</span></button>)}</div>
              </Campo>
              <div className="duas">
                <Campo rotulo="Valor (R$)"><input className="entrada num" inputMode="decimal" value={pag.valor} onChange={(e) => setPag({ ...pag, valor: e.target.value })} /></Campo>
                <Campo rotulo="Data"><input className="entrada num" type="date" max={hojeIso()} value={pag.data} onChange={(e) => setPag({ ...pag, data: e.target.value })} /></Campo>
              </div>
              {erroForm && <p className="erro">{erroForm}</p>}
            </div>
            <div className="acoes"><button className="botao ouro largo" onClick={pagar}>Confirmar recebimento</button></div>
          </>
        )}
      </Folha>
    </>
  );
}
