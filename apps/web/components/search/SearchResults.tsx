import { Users, Globe, TrendingUp, Search } from "lucide-react";
import Link from "next/link";
import { SourceBadge } from "@/components/shared/SourceBadge";
import { DEMO_MODE, demoSearch } from "@/lib/demo";

interface SearchResult {
  id: string;
  tipo: "candidato" | "municipio" | "partido";
  titulo: string;
  subtitulo?: string;
  uf?: string;
  partido_sigla?: string;
  situacao?: string;
  score?: number;
}

interface SearchApiResponse {
  query: string;
  total: number;
  results: SearchResult[];
  tempo_ms?: number;
  meta?: { fonte: string; url?: string };
}

async function fetchResults(query: string, tipo?: string, page = 1): Promise<SearchApiResponse> {
  if (process.env.DEMO_MODE !== "false") {
    const results = demoSearch(query, tipo);
    return { query, total: results.length, results, tempo_ms: 1, meta: { fonte: "Demonstração local", url: "https://dadosabertos.tse.jus.br" } };
  }
  try {
    const params = new URLSearchParams({ q: query, limit: "30", page: String(page) });
    if (tipo) params.set("tipos", tipo);
    const res = await fetch(`${process.env.INTERNAL_API_URL || "http://api:8000"}/api/v1/search?${params}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) throw new Error("API indisponível");
    return res.json();
  } catch {
    const results = demoSearch(query, tipo);
    return {
      query,
      total: results.length,
      results,
      tempo_ms: 1,
      meta: { fonte: "Demonstração local", url: "https://dadosabertos.tse.jus.br" },
    };
  }
}

function getHref(hit: SearchResult) {
  if (hit.tipo === "candidato") return `/candidatos/${hit.id.replace("candidato_", "")}`;
  if (hit.tipo === "municipio") return `/municipios/${hit.id.replace("municipio_", "")}`;
  return `/?q=${encodeURIComponent(hit.titulo)}`;
}

function situacaoBadge(sit?: string) {
  if (!sit) return null;
  const s = sit.toUpperCase();
  if (s.includes("ELEITO") && !s.includes("NÃO")) return { label: "Eleito", cls: "badge-success" };
  if (s.includes("SUPLENTE")) return { label: "Suplente", cls: "badge-info" };
  if (s.includes("CASSAD") || s.includes("INDEFERID")) return { label: "Cassado", cls: "badge-danger" };
  return { label: sit, cls: "badge-neutral" };
}

const TIPO_ICON: Record<string, React.ReactNode> = {
  candidato: <Users size={16} />,
  municipio: <Globe size={16} />,
  partido: <TrendingUp size={16} />,
};

export async function SearchResults({ query, tipo, page }: { query: string; tipo?: string; page: number }) {
  const data = await fetchResults(query, tipo, page);

  if (data.results.length === 0) {
    return (
      <div className="empty-state card">
        <Search size={40} />
        <h3>Nenhum resultado para &ldquo;{query}&rdquo;</h3>
        <p>Tente ajustar o termo de busca ou usar um nome diferente.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
        <div>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            {data.total} resultado{data.total !== 1 ? "s" : ""} para{" "}
          </span>
          <strong style={{ color: "var(--text-primary)" }}>&ldquo;{query}&rdquo;</strong>
          {data.tempo_ms && (
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginLeft: "0.5rem" }}>
              ({data.tempo_ms}ms)
            </span>
          )}
        </div>
        {data.meta && <SourceBadge fonte={data.meta.fonte} url={data.meta.url} />}
      </div>

      {/* Results */}
      {data.results.map((hit) => {
        const badge = situacaoBadge(hit.situacao);
        return (
          <Link key={hit.id} href={getHref(hit)} className="search-result-card">
            <div className={`search-result-icon ${hit.tipo}`}>
              {TIPO_ICON[hit.tipo]}
            </div>
            <div className="search-result-body">
              <span className="search-result-title">{hit.titulo}</span>
              {hit.subtitulo && <span className="search-result-sub">{hit.subtitulo}</span>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginLeft: "auto", flexShrink: 0 }}>
              {hit.uf && <span className="tag">{hit.uf}</span>}
              {badge && <span className={`badge ${badge.cls}`}>{badge.label}</span>}
              <span className={`badge badge-neutral`} style={{ textTransform: "capitalize" }}>
                {hit.tipo}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
