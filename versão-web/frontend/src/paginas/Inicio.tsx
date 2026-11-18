import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Avatar, Carregando, Entrada, Topo, Vazio } from "../componentes/ui";
import type { Resumo } from "../lib/api";
import { useDados } from "../lib/dados";
import { brl, dataBr, diaLongo, hojeIso } from "../lib/formato";

const saudacao = () => { const h = new Date().getHours(); return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"; };

export default function Inicio() {
  const { dados, erro } = useDados<Resumo>("/resumo");
  if (erro) return <><Topo sobre={diaLongo(hojeIso())} titulo={saudacao()} /><p className="erro">{erro}</p></>;
  if (!dados) return <><Topo sobre={diaLongo(hojeIso())} titulo={saudacao()} /><Carregando /></>;
  const agenda = dados.today_rows.filter(([, nomes]) => nomes.some(Boolean));
  return (
    <>
      <Topo sobre={diaLongo(hojeIso())} titulo={saudacao()} />
      <div className="numeros">
        <div className="cartao numero destaque"><span>Alunos ativos</span><strong className="num">{dados.active_students}</strong><small>{dados.total_students} no cadastro</small></div>
        <div className="cartao numero"><span>Atendimentos hoje</span><strong className="num">{dados.today_booked}</strong><small>de {dados.today_capacity} vagas</small></div>
        <div className="cartao numero"><span>Recebido no mês</span><strong className="num">{brl(dados.received_month_cents)}</strong><small>previsto {brl(dados.monthly_revenue_cents)}</small></div>
        <div className="cartao numero"><span>Em atraso</span><strong className="num">{dados.overdue_count}</strong><small>{brl(dados.overdue_cents)}</small></div>
      </div>

      <section className="secao">
        <div className="secao-topo"><h2>Agenda de hoje</h2><Link className="botao mini leve" to="/agenda">Abrir <ChevronRight size={16} /></Link></div>
        {agenda.length ? (
          <div className="cartao recheio lista">
            {agenda.map(([hora, nomes]) => (
              <div key={hora} className="horario" style={{ marginTop: 0 }}>
                <span className="hora num" style={{ paddingTop: 8 }}>{hora}</span>
                <div className="vagas">
                  {nomes.map((nome, i) => (
                    <div key={i} className={nome ? "vaga cheia" : "vaga livre"} style={{ minHeight: 44 }}>
                      {nome ? <span className="meio"><b>{nome}</b><span>{dados.trainer_names[i]}</span></span> : <>Livre · {dados.trainer_names[i]}</>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : <Vazio>Nenhum atendimento marcado hoje.</Vazio>}
      </section>

      <section className="secao">
        <div className="secao-topo"><h2>Próximos vencimentos</h2><Link className="botao mini leve" to="/mensalidades">Ver <ChevronRight size={16} /></Link></div>
        {dados.upcoming.length ? (
          <div className="lista">
            {dados.upcoming.slice(0, 6).map((item, i) => (
              <Entrada key={item.student_id} indice={i}>
                <div className="cartao item">
                  <Avatar nome={item.name} />
                  <span className="meio"><b>{item.name}</b><span>{item.plan_name ?? "Sem plano"}</span></span>
                  <span className="direita"><b className="num">{brl(item.fee_cents)}</b>
                    <span className={`selo ${item.days <= 3 ? "ouro" : ""}`}>{item.days === 0 ? "Hoje" : item.days === 1 ? "Amanhã" : dataBr(item.due_date).slice(0, 5)}</span></span>
                </div>
              </Entrada>
            ))}
          </div>
        ) : <Vazio>Nenhum vencimento definido nas fichas.</Vazio>}
      </section>
    </>
  );
}
