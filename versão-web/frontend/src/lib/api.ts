/* Comunicação com o backend Python. Os nomes dos campos são os mesmos dos
   serviços do desktop (snake_case), para não haver tradução escondida. */

export class ErroApi extends Error {}

async function pedir<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, opcoes);
  } catch {
    throw new ErroApi("Sem conexão com o servidor. Confira se o sistema está ligado.");
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    const detalhe = corpo?.detail;
    throw new ErroApi(typeof detalhe === "string" ? detalhe : "Não foi possível concluir. Confira os campos e tente de novo.");
  }
  return resposta.json() as Promise<T>;
}

const json = (metodo: string, corpo?: unknown): RequestInit => ({
  method: metodo, headers: { "Content-Type": "application/json" }, body: corpo === undefined ? undefined : JSON.stringify(corpo),
});

export const api = {
  get: <T>(caminho: string) => pedir<T>(caminho),
  post: <T>(caminho: string, corpo?: unknown) => pedir<T>(caminho, json("POST", corpo)),
  put: <T>(caminho: string, corpo: unknown) => pedir<T>(caminho, json("PUT", corpo)),
  patch: <T>(caminho: string, corpo: unknown) => pedir<T>(caminho, json("PATCH", corpo)),
  del: <T>(caminho: string) => pedir<T>(caminho, { method: "DELETE" }),
  form: <T>(caminho: string, dados: FormData) => pedir<T>(caminho, { method: "POST", body: dados }),
};

// ---------------------------------------------------------------- tipos
export interface Plano { id: number; name: string; workouts_per_week: number; price_cents: number; duration_months: number; description: string | null; active: boolean }
export interface Aluno {
  id: number; full_name: string; phone: string; birth_date: string | null; cpf: string | null; address: string | null;
  registered_on: string; active: boolean; notes: string | null; plan_id: number | null; plan_name: string | null;
  workouts_per_week: number | null; monthly_fee_cents: number | null; starts_on: string | null; due_day: number | null;
  trainer_id: number | null; trainer_name: string | null;
}
export interface Personal { id: number; name: string; position: number; active: boolean }
export interface Atendimento { id: number; day: string; start_time: string; trainer_id: number; trainer_name: string; student_id: number; student_name: string; status: "agendado" | "concluido" | "falta" | "cancelado"; notes: string | null }
export interface LinhaAgenda { time: string; cells: [Personal, Atendimento | null][]; extra: Atendimento[] }
export interface Agenda { dia: string; linhas: LinhaAgenda[]; semana: { dia: string; ocupadas: number; vagas: number }[] }
export interface Mensalidade { id: number; student_id: number; student_name: string; reference_month: string; amount_cents: number; due_date: string; paid_on: string | null; method: string | null; notes: string | null; status: "Pago" | "Pendente" | "Atrasado" }
export interface ResumoMes { expected_cents: number; received_cents: number; pending_cents: number; overdue_cents: number; paid: number; pending: number; overdue: number; missing: number }
export interface Movimento { id: number; day: string; description: string; category: string; kind: "entrada" | "saida"; amount_cents: number; method: string | null; notes: string | null; payment_id: number | null }
export interface Contrato { id: number; student_id: number; student_name: string; signature_type: string; signed_on: string; file_path: string | null; notes: string | null }
export interface Anamnese { id: number; student_id: number; original_name: string; attached_on: string; size_bytes: number; notes: string | null }
export interface Ficha { aluno: Aluno; horarios_fixos: string[]; proximos: Atendimento[]; mensalidades: Mensalidade[]; contratos: Contrato[]; anamneses: Anamnese[] }
export interface Resumo {
  active_students: number; total_students: number; monthly_revenue_cents: number; received_month_cents: number;
  overdue_count: number; overdue_cents: number; today_booked: number; today_capacity: number;
  today_rows: [string, (string | null)[]][]; trainer_names: string[];
  upcoming: { student_id: number; name: string; plan_name: string | null; fee_cents: number | null; due_date: string; days: number }[];
}
export interface Configuracoes { personais: Personal[]; horario: { open_time: string; close_time: string; slot_minutes: number }; horarios: string[]; categorias_entrada: string[]; categorias_saida: string[] }
export const FORMAS = ["Pix", "Dinheiro", "Débito", "Crédito", "Outro"];
