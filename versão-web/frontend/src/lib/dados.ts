import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Busca dados da API e permite recarregar depois de uma ação. */
export function useDados<T>(caminho: string | null) {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState("");
  const [versao, setVersao] = useState(0);
  useEffect(() => {
    if (!caminho) return;
    let vivo = true;
    setErro("");
    api.get<T>(caminho).then((d) => { if (vivo) setDados(d); }).catch((e: Error) => { if (vivo) setErro(e.message); });
    return () => { vivo = false; };
  }, [caminho, versao]);
  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  return { dados, erro, recarregar };
}
