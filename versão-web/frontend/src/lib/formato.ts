export const brl = (centavos: number | null | undefined) =>
  centavos == null ? "—" : (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const iniciais = (nome: string) => {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "?";
  return (partes.length === 1 ? partes[0].slice(0, 2) : partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
};

export const hojeIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const somarDias = (iso: string, dias: number) => {
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() + dias);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const dataBr = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
};

export const diaLongo = (iso: string) =>
  new Date(iso + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });

export const mesLongo = (mes: string) =>
  new Date(mes.slice(0, 7) + "-15T12:00:00").toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

export const somarMeses = (mes: string, n: number) => {
  const [a, m] = mes.split("-").map(Number);
  const indice = a * 12 + (m - 1) + n;
  return `${Math.floor(indice / 12)}-${String((indice % 12) + 1).padStart(2, "0")}`;
};

export const telefone = (valor: string) => {
  const d = valor.replace(/\D/g, "").replace(/^55(?=\d{10,11}$)/, "");
  if (d.length < 10) return valor;
  return `(${d.slice(0, 2)}) ${d.slice(2, d.length - 4)}-${d.slice(-4)}`;
};

export const mascaraTelefone = (valor: string) => {
  const d = valor.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, d.length - 4)}-${d.slice(-4)}`;
};

/** "450,00" ou "450" -> 45000 centavos. */
export const paraCentavos = (texto: string) => {
  const limpo = texto.replace(/[^\d,.-]/g, "").replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", ".");
  const valor = Number(limpo);
  return Number.isFinite(valor) ? Math.round(valor * 100) : NaN;
};

export const reais = (centavos: number | null | undefined) =>
  centavos == null ? "" : (centavos / 100).toFixed(2).replace(".", ",");
