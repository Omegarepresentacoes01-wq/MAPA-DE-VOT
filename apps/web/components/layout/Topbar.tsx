"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Database } from "lucide-react";
import Link from "next/link";
import { DEMO_MODE, demoSearch } from "@/lib/demo";

interface SearchHit {
  id: string;
  tipo: "candidato" | "municipio" | "partido";
  titulo: string;
  subtitulo?: string;
  uf?: string;
  partido_sigla?: string;
  situacao?: string;
}

const TIPO_ICON: Record<string, string> = {
  candidato: "👤",
  municipio: "🏛️",
  partido: "🎯",
};

const TIPO_HREF = (hit: SearchHit) => {
  if (hit.tipo === "candidato") return `/candidatos/${hit.id.replace("candidato_", "")}`;
  if (hit.tipo === "municipio") return `/municipios/${hit.id.replace("municipio_", "")}`;
  return `/`;
};

export function Topbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const timerRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); setOpen(false); return; }
    setLoading(true);
    if (DEMO_MODE) {
      setResults(demoSearch(q).slice(0, 8));
      setOpen(true);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`/api/v1/search/suggest?q=${encodeURIComponent(q)}&limit=8`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setResults(data.suggestions || []);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => search(query), 200);
    return () => clearTimeout(timerRef.current);
  }, [query, search]);

  // Fecha ao clicar fora
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!dropRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && query.length >= 2) {
      setOpen(false);
      router.push(`/?q=${encodeURIComponent(query)}`);
    }
    if (e.key === "Escape") setOpen(false);
  };

  // Grupos por tipo
  const byType = results.reduce((acc, h) => {
    (acc[h.tipo] ||= []).push(h);
    return acc;
  }, {} as Record<string, SearchHit[]>);

  return (
    <header className="topbar">
      {/* Busca rápida */}
      <div className="topbar-search" ref={dropRef}>
        <Search size={14} className="topbar-search-icon" />
        <input
          ref={inputRef}
          type="search"
          placeholder="Buscar candidato, município, partido…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => query.length >= 2 && setOpen(true)}
          onKeyDown={handleKeyDown}
          aria-label="Busca global"
          aria-expanded={open}
          aria-autocomplete="list"
          id="topbar-search-input"
        />

        {open && results.length > 0 && (
          <div className="search-dropdown" role="listbox" id="search-dropdown">
            {Object.entries(byType).map(([tipo, hits]) => (
              <div key={tipo}>
                <div className="search-dropdown-section">
                  {tipo === "candidato" ? "Candidatos" : tipo === "municipio" ? "Municípios" : "Partidos"}
                </div>
                {hits.map(hit => (
                  <Link
                    key={hit.id}
                    href={TIPO_HREF(hit)}
                    className="search-dropdown-item"
                    onClick={() => { setOpen(false); setQuery(""); }}
                    role="option"
                  >
                    <div className={`search-dropdown-item-icon ${hit.tipo}`}>
                      <span style={{ fontSize: "1rem" }}>{TIPO_ICON[hit.tipo]}</span>
                    </div>
                    <div>
                      <div className="search-dropdown-title">{hit.titulo}</div>
                      {hit.subtitulo && <div className="search-dropdown-sub">{hit.subtitulo}</div>}
                    </div>
                    {hit.situacao && hit.situacao.includes("ELEITO") && (
                      <span className="badge badge-success" style={{ marginLeft: "auto" }}>Eleito</span>
                    )}
                  </Link>
                ))}
              </div>
            ))}
            <div className="search-dropdown-footer">
              <Link href={`/?q=${encodeURIComponent(query)}`} onClick={() => setOpen(false)}>
                Ver todos os resultados para &ldquo;{query}&rdquo; →
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Contexto do ambiente */}
      <div className="topbar-actions">
        <span className="source-meta"><Database size={13} /> Base demonstrativa</span>
      </div>
    </header>
  );
}
