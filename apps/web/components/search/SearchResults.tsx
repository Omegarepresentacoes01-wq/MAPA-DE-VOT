import { Search } from "lucide-react";

export async function SearchResults({ query }: { query: string; tipo?: string; page: number }) {
  return <div className="empty-state card"><Search size={40} /><h3>Busca global ainda não configurada</h3><p>Não exibimos sugestões fictícias. Use Candidatos ou o Mapa para consultar a base oficial já importada.</p><p style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Termo informado: {query}</p></div>;
}
