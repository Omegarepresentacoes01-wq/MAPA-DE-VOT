"use client";

import Link from "next/link";
import { AlertCircle, ArrowRight, CheckCircle2, Search, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { formatNumber, loadOfficialDataset, OfficialDataset } from "@/components/local/official-data";

export function OfficialCandidates() {
  const [dataset, setDataset] = useState<OfficialDataset | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  useEffect(() => { loadOfficialDataset().then(setDataset).catch((cause) => setError(cause.message)); }, []);
  const candidates = useMemo(() => (dataset?.candidates || []).filter((item) => item.nome.toLocaleLowerCase("pt-BR").includes(query.toLocaleLowerCase("pt-BR"))), [dataset, query]);
  return <div>
    <div className="page-header"><h1 style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><Users size={28} style={{ color: "var(--accent)" }} /> Candidatos</h1><p>Resultado oficial do TSE: Governo de Rondônia, 1º turno de 2022.</p></div>
    {error ? <div className="card" style={{ display: "flex", gap: ".75rem", alignItems: "center" }}><AlertCircle color="var(--warning)" /><div><strong>Base oficial não disponível</strong><p style={{ margin: ".25rem 0 0", color: "var(--text-muted)" }}>{error}</p></div></div> : !dataset ? <div className="card">Carregando base oficial…</div> : <>
      <div className="card" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: ".75rem" }}><CheckCircle2 color="var(--success)" size={18} /><span>{dataset.meta.fonte} · {dataset.candidates.length} candidaturas importadas</span><div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: ".5rem" }}><Search size={16} /><input aria-label="Buscar candidato" className="input-field" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar candidatura" /></div></div>
      <div style={{ display: "grid", gap: ".75rem" }}>{candidates.map((candidate) => <Link key={candidate.id} href={`/candidatos/${candidate.id}`} className="search-result-card"><div className="search-result-icon candidato"><Users size={16} /></div><div className="search-result-body"><span className="search-result-title">{candidate.nome}</span><span className="search-result-sub">Governador · RO · 1º turno de 2022</span></div><strong>{formatNumber(candidate.votos)} votos</strong><ArrowRight size={16} style={{ color: "var(--accent)" }} /></Link>)}</div>
    </>}
  </div>;
}
