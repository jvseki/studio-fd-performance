/* "Banco" de demonstração: vive no navegador (localStorage).
   Quando o backend Python existir, só este arquivo e services/payments.ts
   mudam — as telas continuam chamando as mesmas funções. */
import { useSyncExternalStore } from "react";

export type PlanKind = "individual" | "casal";
export interface Plan { id: string; kind: PlanKind; name: string; perWeek: number; cents: number; description: string }
export interface Student { id: string; name: string; phone: string; planId: string; trainer: "Douglas" | "Fran"; since: string; active: boolean }
export type Method = "pix" | "credito";
export interface Charge {
  id: string; studentId: string | null; studentName: string; phone: string; planId: string; cents: number;
  reference: string; dueDate: string; paidAt: string | null; method: Method | null; gatewayId: string | null; linkSentAt: string | null;
}
export interface Session { id: string; day: string; time: string; trainer: "Douglas" | "Fran"; studentName: string; status: "agendado" | "concluido" | "falta" }
export interface Db { students: Student[]; charges: Charge[]; sessions: Session[] }

/* Mesmos planos, personais e horários configurados no aplicativo (v1). */
const individual = (n: number) => `Atendimento personalizado, ${n} treinos por semana.`;
const casal = (n: number) => `Valor do casal, treinando juntos no mesmo horário. ${n} treinos por semana.`;
export const PLANS: Plan[] = [
  { id: "ind-2", kind: "individual", name: "Individual 2x", perWeek: 2, cents: 35000, description: individual(2) },
  { id: "ind-3", kind: "individual", name: "Individual 3x", perWeek: 3, cents: 45000, description: individual(3) },
  { id: "ind-4", kind: "individual", name: "Individual 4x", perWeek: 4, cents: 55000, description: individual(4) },
  { id: "ind-5", kind: "individual", name: "Individual 5x", perWeek: 5, cents: 65000, description: individual(5) },
  { id: "cas-2", kind: "casal", name: "Casal 2x", perWeek: 2, cents: 60000, description: casal(2) },
  { id: "cas-3", kind: "casal", name: "Casal 3x", perWeek: 3, cents: 70000, description: casal(3) },
];
export const TRAINERS = ["Douglas", "Fran"] as const;
export const STUDIO = { open: "06:00", close: "21:00", slotMinutes: 60, city: "Andradina · SP" };
export const plan = (id: string) => PLANS.find((item) => item.id === id) ?? PLANS[1];
export const TIMES = Array.from({ length: 15 }, (_, i) => `${String(6 + i).padStart(2, "0")}:00`); // 06:00 … 20:00

const iso = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
export const today = () => iso(new Date());
const shift = (days: number) => { const d = new Date(); d.setDate(d.getDate() + days); return iso(d); };
const monthRef = (offset = 0) => {
  const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + offset);
  return d.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }).replace(" de ", " ");
};
const dueThisMonth = (day: number, offset = 0) => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + offset); d.setDate(day); return iso(d); };

function seed(): Db {
  const people: [string, string, "Douglas" | "Fran", number][] = [
    ["Ana Beatriz Souza", "ind-3", "Douglas", 5], ["Bruno Carvalho", "ind-2", "Fran", 10], ["Carla Mendes", "ind-5", "Douglas", 15],
    ["Diego Ramos", "ind-3", "Fran", 5], ["Eduarda Lima", "ind-2", "Douglas", 10], ["Felipe Nogueira", "ind-4", "Fran", 15],
    ["Gabriela Rocha", "cas-3", "Douglas", 5], ["Henrique Alves", "cas-3", "Douglas", 5], ["Isabela Torres", "ind-4", "Fran", 10],
    ["João Pedro Martins", "ind-3", "Douglas", 15], ["Juliana Santos", "ind-2", "Fran", 10], ["Lucas Ferreira", "ind-5", "Douglas", 5],
  ];
  const students: Student[] = people.map(([name, planId, trainer], index) => ({
    id: `a${index + 1}`, name, phone: `189970000${String(index).padStart(2, "0")}`, planId, trainer, since: shift(-200 + index * 9), active: true,
  }));
  const charges: Charge[] = [];
  people.forEach(([name, planId, , dueDay], index) => {
    const student = students[index];
    const half = plan(planId).kind === "casal" ? plan(planId).cents / 2 : plan(planId).cents;
    // mês passado: quase todos pagos
    const lastDue = dueThisMonth(dueDay, -1);
    const lastPaid = index !== 9;
    charges.push({ id: `m0-${student.id}`, studentId: student.id, studentName: name, phone: student.phone, planId, cents: half, reference: monthRef(-1),
      dueDate: lastDue, paidAt: lastPaid ? lastDue : null, method: lastPaid ? (index % 3 === 0 ? "credito" : "pix") : null,
      gatewayId: lastPaid ? `MP-${88100 + index * 37}` : null, linkSentAt: lastDue });
    // mês atual
    const due = dueThisMonth(dueDay);
    const paid = due <= today() && index % 3 !== 1;
    charges.push({ id: index === 0 ? "ana-mensalidade" : `m1-${student.id}`, studentId: student.id, studentName: name, phone: student.phone, planId, cents: half,
      reference: monthRef(), dueDate: due, paidAt: paid && index !== 0 ? due : null, method: paid && index !== 0 ? (index % 2 ? "pix" : "credito") : null,
      gatewayId: paid && index !== 0 ? `MP-${90400 + index * 53}` : null, linkSentAt: index % 4 === 3 ? null : shift(-2) });
  });
  const sessions: Session[] = [];
  const grid: [string, string, string][] = [["06:00", "Ana Beatriz Souza", "Bruno Carvalho"], ["07:00", "Carla Mendes", "Diego Ramos"], ["08:00", "Eduarda Lima", ""],
    ["09:00", "Gabriela Rocha", "Isabela Torres"], ["17:00", "João Pedro Martins", "Felipe Nogueira"], ["18:00", "Lucas Ferreira", "Juliana Santos"], ["19:00", "Henrique Alves", ""]];
  for (let offset = -1; offset <= 5; offset++) {
    grid.forEach(([time, douglas, fran], index) => {
      if ((offset + index) % 5 === 4) return;
      const status = offset < 0 ? (index === 2 ? "falta" : "concluido") : "agendado";
      if (douglas) sessions.push({ id: `s${offset}-${index}-d`, day: shift(offset), time, trainer: "Douglas", studentName: douglas, status });
      if (fran) sessions.push({ id: `s${offset}-${index}-f`, day: shift(offset), time, trainer: "Fran", studentName: fran, status });
    });
  }
  return { students, charges, sessions };
}

const KEY = "studiofd.v2.demo";
let db: Db = load();
const listeners = new Set<() => void>();

function load(): Db {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as Db;
  } catch { /* armazenamento indisponível: segue com dados em memória */ }
  return seed();
}
function commit(next: Db) {
  db = next;
  try { localStorage.setItem(KEY, JSON.stringify(db)); } catch { /* idem */ }
  listeners.forEach((listener) => listener());
}
window.addEventListener("storage", (event) => {
  if (event.key === KEY && event.newValue) { db = JSON.parse(event.newValue) as Db; listeners.forEach((listener) => listener()); }
});

export const useDb = () => useSyncExternalStore((listener) => { listeners.add(listener); return () => listeners.delete(listener); }, () => db);
export const getDb = () => db;
export const resetDemo = () => commit(seed());

export type ChargeStatus = "pago" | "pendente" | "atrasado";
export const chargeStatus = (charge: Charge): ChargeStatus => (charge.paidAt ? "pago" : charge.dueDate < today() ? "atrasado" : "pendente");

export function markPaid(id: string, method: Method, gatewayId: string) {
  commit({ ...db, charges: db.charges.map((c) => (c.id === id ? { ...c, paidAt: today(), method, gatewayId } : c)) });
}
export function undoPaid(id: string) {
  commit({ ...db, charges: db.charges.map((c) => (c.id === id ? { ...c, paidAt: null, method: null, gatewayId: null } : c)) });
}
export function markSent(id: string) {
  commit({ ...db, charges: db.charges.map((c) => (c.id === id ? { ...c, linkSentAt: today() } : c)) });
}
export function updateCharge(id: string, patch: Partial<Charge>) {
  commit({ ...db, charges: db.charges.map((c) => (c.id === id ? { ...c, ...patch } : c)) });
}
export function createCharge(input: { studentName: string; phone: string; planId: string; cents: number; dueDate: string; studentId?: string | null }): Charge {
  const slug = input.studentName.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 18);
  const charge: Charge = { id: `${slug || "aluno"}-${Math.random().toString(36).slice(2, 7)}`, studentId: input.studentId ?? null, studentName: input.studentName,
    phone: input.phone, planId: input.planId, cents: input.cents, reference: monthRef(), dueDate: input.dueDate, paidAt: null, method: null, gatewayId: null, linkSentAt: null };
  commit({ ...db, charges: [charge, ...db.charges] });
  return charge;
}
export function addSession(session: Omit<Session, "id">): string | null {
  const here = db.sessions.filter((s) => s.day === session.day && s.time === session.time);
  if (here.some((s) => s.trainer === session.trainer)) return `${session.trainer} já tem aluno nesse horário.`;
  commit({ ...db, sessions: [...db.sessions, { ...session, id: `s-${Date.now()}` }] });
  return null;
}
export function setSessionStatus(id: string, status: Session["status"] | "remover") {
  commit({ ...db, sessions: status === "remover" ? db.sessions.filter((s) => s.id !== id) : db.sessions.map((s) => (s.id === id ? { ...s, status } : s)) });
}
export const payLink = (id: string) => `${location.origin}/pagar/${id}`;
