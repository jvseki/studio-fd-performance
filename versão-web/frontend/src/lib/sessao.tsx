import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Usuario } from "./api";

interface Sessao { usuario: Usuario | null | undefined; entrar: (email: string, senha: string) => Promise<void>; sair: () => Promise<void> }
const SessaoCtx = createContext<Sessao>({ usuario: undefined, entrar: async () => {}, sair: async () => {} });
export const useSessao = () => useContext(SessaoCtx);

/** undefined = conferindo; null = precisa entrar; Usuario = dentro do sistema. */
export function SessaoProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined);
  useEffect(() => {
    api.get<Usuario>("/eu").then(setUsuario).catch(() => setUsuario(null));
    const expirou = () => setUsuario(null);
    window.addEventListener("studiofd:sessao-expirada", expirou);
    return () => window.removeEventListener("studiofd:sessao-expirada", expirou);
  }, []);
  const entrar = useCallback(async (email: string, senha: string) => { setUsuario(await api.post<Usuario>("/entrar", { email, senha })); }, []);
  const sair = useCallback(async () => { await api.post("/sair").catch(() => {}); setUsuario(null); }, []);
  return <SessaoCtx.Provider value={{ usuario, entrar, sair }}>{children}</SessaoCtx.Provider>;
}
