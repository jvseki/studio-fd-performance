import "@fontsource-variable/manrope";
import "@fontsource/instrument-serif/400.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { aplicarTema } from "./lib/tema";
import "./estilo.css";

aplicarTema();

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
