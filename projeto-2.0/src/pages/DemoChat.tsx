/* Tela de conversa usada só no vídeo de demonstração: mostra como o aluno
   recebe o link. Não é o WhatsApp de verdade nem envia nada. */
import { motion } from "motion/react";
import { ChevronLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { useDb } from "../data/store";
import { brl } from "../lib/format";
import { EASE } from "../lib/motion";
import "../styles/chat.css";

export default function DemoChat() {
  const charge = useDb().charges.find((item) => item.id === "ana-mensalidade");
  if (!charge) return null;
  const first = charge.studentName.split(" ")[0];
  const bubble = (delay: number) => ({ initial: { opacity: 0, y: 16, scale: 0.96 }, animate: { opacity: 1, y: 0, scale: 1 }, transition: { delay, duration: 0.45, ease: EASE } });
  return (
    <div className="chat">
      <header><ChevronLeft size={22} /><span className="chat-avatar serif">FD</span><div><b>Studio FD Performance</b><i>online</i></div></header>
      <div className="chat-body">
        <span className="chat-day">Hoje</span>
        <motion.p className="bubble" {...bubble(0.5)}>Oi, {first}! Tudo bem? 💪<time>09:12</time></motion.p>
        <motion.p className="bubble" {...bubble(1.5)}>Segue o link da sua mensalidade de {charge.reference}. Dá para pagar por Pix ou cartão.<time>09:12</time></motion.p>
        <motion.div className="bubble link" {...bubble(2.6)}>
          <Link to={`/pagar/${charge.id}`} id="link-pagamento">
            <span className="link-card">
              <span className="link-mark serif">FD</span>
              <span><b>Mensalidade · {brl(charge.cents)}</b><i>Studio FD Performance — pagamento seguro</i></span>
            </span>
            <u>studiofd.com.br/pagar/{charge.id}</u>
          </Link>
          <time>09:12</time>
        </motion.div>
      </div>
      <footer><span>Mensagem</span></footer>
    </div>
  );
}
