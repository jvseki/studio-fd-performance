/* Camada de pagamento.

   HOJE (só frontend): modo demonstração. Nada é cobrado; o "pagamento"
   é simulado e gravado no navegador.

   DEPOIS (com backend Python): estas mesmas funções passam a chamar a API
   (VITE_API_URL), que fala com o Mercado Pago usando o Access Token guardado
   no servidor. O navegador só conhece a chave PÚBLICA (VITE_MP_PUBLIC_KEY),
   usada pelo SDK do Mercado Pago para transformar o cartão em um token —
   os dados do cartão nunca passam pelo nosso servidor.

   Fluxo real previsto:
     Pix     POST {API}/pagamentos/pix      -> { id, qr_code, qr_code_base64, expira_em }
     Cartão  POST {API}/pagamentos/cartao   { token, parcelas, cobranca_id } -> { id, status }
     Aviso   Mercado Pago -> POST {API}/webhooks/mercadopago -> marca a cobrança como paga
*/
import { markPaid, type Charge } from "../data/store";

export const MP_PUBLIC_KEY: string = import.meta.env.VITE_MP_PUBLIC_KEY ?? "";
export const API_URL: string = import.meta.env.VITE_API_URL ?? "";
// Esta versão é apenas frontend. Variáveis de ambiente não habilitam cobranças.
// Só remover esta trava após implementar e validar a confirmação pelo backend.
export const DEMO_MODE = true;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const receipt = () => `DEMO-${Date.now().toString().slice(-8)}`;

export interface PixCharge { payload: string; expiresInMinutes: number }

/** Gera o Pix da cobrança. No modo demonstração o código não é pagável. */
export async function createPix(charge: Charge): Promise<PixCharge> {
  await wait(700);
  return { payload: `DEMONSTRACAO-STUDIO-FD-${charge.id.toUpperCase()}-NAO-PAGAVEL-${charge.cents}`, expiresInMinutes: 30 };
}

/** No real, quem confirma é o aviso do Mercado Pago ao backend; aqui simulamos. */
export async function confirmPix(charge: Charge): Promise<string> {
  await wait(1600);
  const id = receipt();
  markPaid(charge.id, "pix", id);
  return id;
}

export interface CardInput { number: string; holder: string; expiry: string; cvv: string; installments: number }

/** No real: o SDK do Mercado Pago gera um token do cartão e só o token vai ao backend. */
export async function payWithCard(charge: Charge, _card: CardInput): Promise<string> {
  await wait(2300);
  const id = receipt();
  markPaid(charge.id, "credito", id);
  return id;
}
