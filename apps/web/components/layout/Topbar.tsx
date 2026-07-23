"use client";

import { Database } from "lucide-react";

// A navegação atual não usa uma barra de busca global. Mantemos apenas o contexto
// da base, sem sugerir registros que não foram importados.
export function Topbar() {
  return <header className="topbar"><div className="topbar-actions"><span className="source-meta"><Database size={13} /> Dados oficiais importados localmente</span></div></header>;
}
