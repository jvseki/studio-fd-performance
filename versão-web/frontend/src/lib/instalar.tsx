/* Parte "Versão PWA (aplicativo)" da tela Mais.
   - Android: botão que abre a janela de instalar do Chrome.
   - iPhone/iPad: passo a passo do Safari (a Apple não deixa instalar por botão).
   - Computador: passo a passo do Chrome/Edge (e o botão, se o navegador oferecer).
   - Já aberto como app: só avisa que está instalado. */
import { CheckCircle2, Download, PlusSquare, Share } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { Folha } from "../componentes/ui";

interface EventoInstalar extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: "accepted" | "dismissed" }> }

let pedido: EventoInstalar | null = null;
let instalado = false;
const ouvintes = new Set<() => void>();
const avisar = () => ouvintes.forEach((f) => f());

// Precisa ser registrado logo que o site carrega (o navegador dispara cedo).
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); pedido = e as EventoInstalar; avisar(); });
window.addEventListener("appinstalled", () => { instalado = true; pedido = null; avisar(); });

const abertoComoApp = () =>
  window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
const ua = navigator.userAgent;
const ehIos = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const ehAndroid = /android/i.test(ua);

function useAparelho() {
  useSyncExternalStore((f) => { ouvintes.add(f); return () => ouvintes.delete(f); }, () => `${!!pedido}-${instalado}`);
  const aparelho = ehIos ? "iphone" : ehAndroid ? "android" : "computador";
  return { aparelho, instalado: instalado || abertoComoApp(), pronto: !!pedido } as const;
}

async function abrirJanela() {
  if (!pedido) return false;
  await pedido.prompt();
  const escolha = await pedido.userChoice;
  if (escolha.outcome === "accepted") instalado = true;
  pedido = null;
  avisar();
  return true;
}

const icone = { size: 18, style: { verticalAlign: -3 } };

export function SecaoPwa() {
  const { aparelho, instalado: jaInstalado, pronto } = useAparelho();
  const [ajudaAndroid, setAjudaAndroid] = useState(false);

  let corpo;
  if (jaInstalado) {
    corpo = <p className="pwa-ok"><CheckCircle2 /> O app já está instalado neste aparelho.</p>;
  } else if (aparelho === "android") {
    corpo = (
      <>
        <p className="pequeno fraco" style={{ marginTop: 0, marginBottom: 14 }}>Coloque o Studio FD na tela inicial do celular, como um aplicativo.</p>
        <button className="botao ouro largo" onClick={async () => { if (!(await abrirJanela())) setAjudaAndroid(true); }}><Download /> Instalar app</button>
        <Folha aberta={ajudaAndroid} titulo="Instalar no Android" aoFechar={() => setAjudaAndroid(false)}>
          <ol className="passos">
            <li>Abra este site no <b>Chrome</b>.</li>
            <li>Toque nos <b>três pontinhos ⋮</b> no canto de cima.</li>
            <li>Toque em <b>Instalar app</b> (ou <b>Adicionar à tela inicial</b>) e confirme.</li>
          </ol>
          <div className="acoes"><button className="botao ouro largo" onClick={() => setAjudaAndroid(false)}>Entendi</button></div>
        </Folha>
      </>
    );
  } else if (aparelho === "iphone") {
    corpo = (
      <ol className="passos">
        <li>Abra este site no <b>Safari</b> (no iPhone, só o Safari instala).</li>
        <li>Toque em <b>Compartilhar</b> <Share {...icone} /> na barra do Safari.</li>
        <li>Role e toque em <b>Adicionar à Tela de Início</b> <PlusSquare {...icone} />.</li>
        <li>Toque em <b>Adicionar</b> e abra pelo ícone <b>Studio FD</b>.</li>
      </ol>
    );
  } else {
    corpo = (
      <>
        <ol className="passos">
          <li>Use o <b>Google Chrome</b> ou o <b>Microsoft Edge</b>.</li>
          <li>Na barra de endereço, à direita, clique no ícone de <b>instalar</b> (um monitor com uma setinha).</li>
          <li>Ou abra o menu <b>⋮</b> → <b>Transmitir, salvar e compartilhar</b> → <b>Instalar página como app</b> (no Edge: menu <b>…</b> → <b>Aplicativos</b> → <b>Instalar este site</b>).</li>
          <li>Clique em <b>Instalar</b>. O Studio FD abre numa janela própria e ganha atalho na Área de Trabalho.</li>
        </ol>
        {pronto && <button className="botao ouro largo" style={{ marginTop: 14 }} onClick={abrirJanela}><Download /> Instalar agora</button>}
      </>
    );
  }

  return (
    <section style={{ marginBottom: 16 }}>
      <p className="pequeno fraco" style={{ fontWeight: 800, marginBottom: 8 }}>Versão PWA (aplicativo)</p>
      <div className="cartao recheio">{corpo}</div>
    </section>
  );
}
