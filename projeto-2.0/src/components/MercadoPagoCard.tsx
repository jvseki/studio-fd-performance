/* Formulário de cartão OFICIAL do Mercado Pago (Card Payment Brick).
   Reservado para a etapa do backend. O Brick
   transforma o cartão em um token dentro do navegador e só o token segue
   para o backend, que faz a cobrança com o Access Token guardado no servidor. */
import { CardPayment, initMercadoPago } from "@mercadopago/sdk-react";
import { useEffect, useState } from "react";
import { type Charge } from "../data/store";
import { API_URL, DEMO_MODE, MP_PUBLIC_KEY } from "../services/payments";

let started = false;

export default function MercadoPagoCard({ charge }: { charge: Charge }) {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  useEffect(() => { if (!DEMO_MODE && !started) { initMercadoPago(MP_PUBLIC_KEY, { locale: "pt-BR" }); started = true; } }, []);
  if (DEMO_MODE) return <p className="hint">Pagamentos reais indisponíveis nesta demonstração.</p>;
  if (pending) return <p role="status">Solicitação enviada. Aguarde a confirmação pelo Studio.</p>;
  return (
    <div>
      <CardPayment
        initialization={{ amount: charge.cents / 100 }}
        customization={{ visual: { style: { theme: "dark" } }, paymentMethods: { maxInstallments: 3 } }}
        onSubmit={async (data) => {
          setError("");
          const response = await fetch(`${API_URL}/pagamentos/cartao`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cobranca_id: charge.id, token: data.token, parcelas: data.installments, bandeira: data.payment_method_id, emissor: data.issuer_id, pagador: data.payer }),
          });
          const result = await response.json();
          if (!response.ok) { setError(result.mensagem ?? "Não foi possível enviar o pagamento."); throw new Error("recusado"); }
          // A resposta do envio não comprova pagamento. Na etapa do backend,
          // consultar a cobrança cuja confirmação virá do webhook verificado.
          // Nunca dar baixa no localStorage a partir desta resposta.
          setPending(true);
        }}
        onError={() => setError("Não foi possível carregar o formulário do Mercado Pago.")}
      />
      {error && <p className="hint" role="alert" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
}
