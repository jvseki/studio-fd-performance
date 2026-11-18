import { Check, ChevronLeft, ChevronRight, Plus, Trash2, UserX, X } from "lucide-react";
import { useState } from "react";
import { Avatar, Campo, Carregando, Folha, Topo, useAviso } from "../componentes/ui";
import { api, type Agenda as AgendaDia, type Aluno, type Atendimento, type Personal } from "../lib/api";
import { useDados } from "../lib/dados";
import { diaLongo, hojeIso, somarDias } from "../lib/formato";

const SITUACAO: Record<string, string> = { agendado: "Agendado", concluido: "Concluído", falta: "Falta" };
const DIAS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];

export default function Agenda() {
  const [dia, setDia] = useState(hojeIso());
  const { dados, erro, recarregar } = useDados<AgendaDia>(`/agenda?dia=${dia}`);
  const alunos = useDados<Aluno[]>("/alunos?ativo=true").dados ?? [];
  const avisar = useAviso();
  const [nova, setNova] = useState<{ time: string; personal: Personal } | null>(null);
  const [aberto, setAberto] = useState<Atendimento | null>(null);
  const [form, setForm] = useState({ aluno: "", semanas: "12", repetir: true });
  const [erroForm, setErroForm] = useState("");
  const agoraMin = new Date().getHours() * 60 + new Date().getMinutes();

  const agendar = async () => {
    if (!nova || !form.aluno) { setErroForm("Escolha o aluno."); return; }
    try {
      const r = await api.post<{ created: string[]; skipped: [string, string][] }>("/agenda", {
        student_id: Number(form.aluno), day: dia, time: nova.time, trainer_id: nova.personal.id,
        repeat_weeks: form.repetir ? Math.max(0, Number(form.semanas) - 1) : 0,
      });
      avisar(`${r.created.length} horário(s) agendado(s)${r.skipped.length ? ` · ${r.skipped.length} semana(s) lotada(s)` : ""}`);
      setNova(null); recarregar();
    } catch (e) { setErroForm((e as Error).message); }
  };
  const mudar = async (acao: string) => {
    if (!aberto) return;
    try {
      if (acao === "remover" || acao === "serie") await api.del(`/agenda/${aberto.id}${acao === "serie" ? "?serie=true" : ""}`);
      else await api.patch(`/agenda/${aberto.id}`, { status: acao });
      avisar(acao === "remover" || acao === "serie" ? "Horário desmarcado" : `Marcado como ${SITUACAO[acao].toLowerCase()}`);
      setAberto(null); recarregar();
    } catch (e) { avisar((e as Error).message, true); }
  };

  return (
    <>
      <Topo sobre="Agenda" titulo={dia === hojeIso() ? "Hoje" : diaLongo(dia).split(",")[0]} />
      <div className="navegador">
        <button className="botao redondo" aria-label="Dia anterior" onClick={() => setDia(somarDias(dia, -1))}><ChevronLeft /></button>
        <span className="rotulo cap">{diaLongo(dia)}</span>
        <button className="botao redondo" aria-label="Próximo dia" onClick={() => setDia(somarDias(dia, 1))}><ChevronRight /></button>
      </div>
      {dados && (
        <div className="semana">
          {dados.semana.map((d) => (
            <button key={d.dia} className={`dia ${d.dia === dia ? "ativo" : ""}`} onClick={() => setDia(d.dia)} aria-label={diaLongo(d.dia)}>
              {DIAS[new Date(d.dia + "T12:00:00").getDay()]}
              <strong className="num">{Number(d.dia.slice(8))}</strong>
              <i><b style={{ width: `${d.vagas ? (d.ocupadas / d.vagas) * 100 : 0}%` }} /></i>
            </button>
          ))}
        </div>
      )}
      {erro && <p className="erro">{erro}</p>}
      {!dados ? <Carregando linhas={6} /> : (
        <div>
          {dados.linhas.map((linha) => {
            const [h, m] = linha.time.split(":").map(Number);
            const agora = dia === hojeIso() && agoraMin >= h * 60 + m && agoraMin < h * 60 + m + 60;
            return (
              <div className="horario" key={linha.time}>
                <span className={`hora num ${agora ? "agora" : ""}`}>{linha.time}</span>
                <div className="vagas">
                  {linha.cells.map(([personal, item]) => item ? (
                    <button key={personal.id} className={`vaga cheia ${item.status}`} onClick={() => setAberto(item)}>
                      <Avatar nome={item.student_name} />
                      <span className="meio"><b>{item.student_name}</b><span>{personal.name} · {SITUACAO[item.status]}</span></span>
                    </button>
                  ) : (
                    <button key={personal.id} className="vaga livre" onClick={() => { setNova({ time: linha.time, personal }); setErroForm(""); setForm({ aluno: "", semanas: "12", repetir: true }); }}>
                      <Plus size={18} /> {personal.name}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Folha aberta={!!nova} titulo={`Agendar ${nova?.time ?? ""}`} aoFechar={() => setNova(null)}>
        <div className="campos">
          <p className="fraco">Com {nova?.personal.name} · <span className="cap" style={{ display: "inline-block" }}>{diaLongo(dia)}</span></p>
          <Campo rotulo="Aluno">
            <select className="entrada" value={form.aluno} onChange={(e) => setForm({ ...form, aluno: e.target.value })}>
              <option value="">Escolha o aluno…</option>
              {alunos.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
            </select>
          </Campo>
          <div className="opcoes">
            <button className={`opcao ${form.repetir ? "ativa" : ""}`} onClick={() => setForm({ ...form, repetir: !form.repetir })}>
              Horário fixo (repetir toda semana) {form.repetir ? <Check size={20} /> : <X size={20} />}
            </button>
          </div>
          {form.repetir && (
            <Campo rotulo="Por quantas semanas">
              <select className="entrada" value={form.semanas} onChange={(e) => setForm({ ...form, semanas: e.target.value })}>
                {[4, 8, 12, 24, 52].map((n) => <option key={n} value={n}>{n} semanas</option>)}
              </select>
            </Campo>
          )}
          {erroForm && <p className="erro">{erroForm}</p>}
        </div>
        <div className="acoes"><button className="botao ouro largo" onClick={agendar}>Agendar</button></div>
      </Folha>

      <Folha aberta={!!aberto} titulo={aberto?.student_name ?? ""} aoFechar={() => setAberto(null)}>
        <p className="fraco" style={{ marginBottom: 14 }}>{aberto?.start_time} com {aberto?.trainer_name} · {aberto ? SITUACAO[aberto.status] : ""}</p>
        <div className="acoes" style={{ marginTop: 0 }}>
          <button className="botao largo" onClick={() => mudar("concluido")}><Check /> Compareceu</button>
          <button className="botao largo" onClick={() => mudar("falta")}><UserX /> Faltou</button>
          {aberto?.status !== "agendado" && <button className="botao largo leve" onClick={() => mudar("agendado")}>Voltar para agendado</button>}
          <button className="botao largo perigo" onClick={() => mudar("remover")}><Trash2 /> Desmarcar só este dia</button>
          <button className="botao largo leve" onClick={() => mudar("serie")}>Desmarcar este e os próximos</button>
        </div>
      </Folha>
    </>
  );
}
