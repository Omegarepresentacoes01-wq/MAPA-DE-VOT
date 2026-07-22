"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { Search, Zap, ChevronRight } from "lucide-react";
import "./search-hero.css";

const PLACEHOLDERS = [
  "Buscar candidato pelo nome…",
  "Pesquisar município…",
  "Encontrar partido político…",
  "Ex: Lula, São Paulo, PT…",
];

export function SearchHero() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [placeholder, setPlaceholder] = useState(PLACEHOLDERS[0]);
  const [pIdx, setPIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Placeholder rotativo
  useEffect(() => {
    const timer = setInterval(() => {
      setPIdx(i => (i + 1) % PLACEHOLDERS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    setPlaceholder(PLACEHOLDERS[pIdx]);
  }, [pIdx]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    router.push(`/?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <section className="search-hero">
      {/* Background decorativo */}
      <div className="search-hero-glow" aria-hidden="true" />
      <div className="search-hero-grid" aria-hidden="true" />

      <div className="search-hero-content">
        {/* Badge */}
        <div className="search-hero-badge">
          <Zap size={12} />
          Dados oficiais TSE + IBGE · Eleições 2022
        </div>

        {/* Headline */}
        <h1 className="search-hero-title">
          Inteligência
          <span className="search-hero-title-accent"> Eleitoral</span>
          <br />e Territorial
        </h1>
        <p className="search-hero-subtitle">
          Candidatos, resultados, finanças, mapas e comparações — com rastreabilidade total de fonte.
        </p>

        {/* Search form */}
        <form className="search-hero-form" onSubmit={handleSubmit} role="search">
          <div className="search-hero-input-wrap">
            <Search size={18} className="search-hero-icon" aria-hidden="true" />
            <input
              ref={inputRef}
              id="hero-search"
              type="search"
              className="search-hero-input"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={placeholder}
              autoComplete="off"
              aria-label="Busca global — candidato, município ou partido"
            />
            <button
              type="submit"
              className="search-hero-btn"
              disabled={!query.trim()}
              aria-label="Executar busca"
            >
              Buscar <ChevronRight size={14} />
            </button>
          </div>
        </form>

        {/* Sugestões rápidas */}
        <div className="search-hero-suggestions">
          <span>Destaques:</span>
          {["Lula", "Bolsonaro", "São Paulo", "PT", "PL"].map(s => (
            <button
              key={s}
              className="search-hero-chip"
              onClick={() => { setQuery(s); router.push(`/?q=${encodeURIComponent(s)}`); }}
              type="button"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
