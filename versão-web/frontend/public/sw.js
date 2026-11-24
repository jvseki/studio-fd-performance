/* Service worker do Studio FD: guarda as TELAS (para abrir rápido e instalar
   como app). Os DADOS (/api) sempre vêm do servidor — nunca do cache. */
const VERSAO = "studiofd-v1";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(VERSAO).then((cache) => cache.addAll(["/", "/manifest.webmanifest", "/icones/icone-192.png"])));
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(caches.keys().then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n)))));
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  const url = new URL(pedido.url);
  if (pedido.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  if (pedido.mode === "navigate") {
    // Páginas: tenta a rede; sem internet, abre a última versão guardada.
    evento.respondWith(fetch(pedido).then((resposta) => {
      const copia = resposta.clone();
      caches.open(VERSAO).then((cache) => cache.put("/", copia));
      return resposta;
    }).catch(() => caches.match("/")));
    return;
  }
  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/icones/")) {
    // Arquivos com nome versionado: cache primeiro, rede se faltar.
    evento.respondWith(caches.match(pedido).then((guardado) => guardado || fetch(pedido).then((resposta) => {
      const copia = resposta.clone();
      caches.open(VERSAO).then((cache) => cache.put(pedido, copia));
      return resposta;
    })));
  }
});
