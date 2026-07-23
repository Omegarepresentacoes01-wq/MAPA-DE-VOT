"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ArrowLeftRight, MapPinned } from "lucide-react";
import { SourceBadge } from "@/components/shared/SourceBadge";
import { formatNumber, loadOfficialDataset, OfficialDataset } from "@/components/local/official-data";

export function Comparador() {
  const [dataset, setDataset] = useState<OfficialDataset | null>(null);
  const [error, setError] = useState("");
  const [candidateA, setCandidateA] = useState("");
  const [candidateB, setCandidateB] = useState("");
  const [municipality, setMunicipality] = useState("");
  useEffect(() => { loadOfficialDataset().then((data) => { setDataset(data); setCandidateA(data.candidates[0]?.id || ""); setCandidateB(data.candidates[1]?.id || data.candidates[0]?.id || ""); setMunicipality(data.mapa.features[0]?.properties.codigo_ibge || ""); }).catch((cause) => setError(cause.message)); }, []);
  const selectedMunicipality = dataset?.mapa.features.find((item) => item.properties.codigo_ibge === municipality);
  const a = dataset?.candidates.find((item) => item.id === candidateA);
  const b = dataset?.candidates.find((item) => item.id === candidateB);
  const votesA = selectedMunicipality?.properties.votos[candidateA] || 0;
  const votesB = selectedMunicipality?.properties.votos[candidateB] || 0;
  const difference = votesA - votesB;
  const ranking = useMemo(() => dataset && a && b ? dataset.mapa.features.map((feature) => ({ nome: feature.properties.nome, votosA: feature.properties.votos[a.id] || 0, votosB: feature.properties.votos[b.id] || 0 })).sort((left, right) => Math.abs(right.votosA - right.votosB) - Math.abs(left.votosA - left.votosB)) : [], [dataset, a, b]);
  return <div><div className="page-header"><h1 style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><ArrowLeftRight size={28} style={{ color: "var(--accent)" }} /> Comparador</h1><p>Compare duas candidaturas no mesmo resultado oficial: Rondônia, governador, 1º turno de 2022.</p></div>
    {error ? <div className="card"><AlertCircle color="var(--warning)" /> {error}</div> : !dataset ? <div className="card">Carregando base oficial…</div> : <><div className="card" style={{ marginBottom: "1.5rem" }}><div className="grid-3"><label className="field-label">Candidatura A<select className="input-field" value={candidateA} onChange={(event) => setCandidateA(event.target.value)}>{dataset.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.nome}</option>)}</select></label><label className="field-label">Candidatura B<select className="input-field" value={candidateB} onChange={(event) => setCandidateB(event.target.value)}>{dataset.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.nome}</option>)}</select></label><label className="field-label">Município<select className="input-field" value={municipality} onChange={(event) => setMunicipality(event.target.value)}>{dataset.mapa.features.map((feature) => <option key={feature.properties.codigo_ibge} value={feature.properties.codigo_ibge}>{feature.properties.nome}</option>)}</select></label></div></div>
      <div className="grid-3" style={{ marginBottom: "1.5rem" }}><div className="stat-card"><div className="stat-label">{a?.nome || "Candidatura A"}</div><div className="stat-value">{formatNumber(votesA)}</div><div className="stat-sub">{selectedMunicipality?.properties.nome}</div></div><div className="stat-card"><div className="stat-label">{b?.nome || "Candidatura B"}</div><div className="stat-value">{formatNumber(votesB)}</div><div className="stat-sub">{selectedMunicipality?.properties.nome}</div></div><div className="stat-card"><div className="stat-label">Diferença A − B</div><div className="stat-value" style={{ color: difference >= 0 ? "var(--success)" : "var(--danger)" }}>{difference > 0 ? "+" : ""}{formatNumber(difference)}</div><div className="stat-sub">Votos no município selecionado</div></div></div>
      <section className="card" style={{ padding: 0, overflow: "hidden" }}><div className="section-title" style={{ padding: "1rem" }}><MapPinned size={17} /> Diferença por município</div><table className="data-table"><thead><tr><th>Município</th><th style={{ textAlign: "right" }}>{a?.nome}</th><th style={{ textAlign: "right" }}>{b?.nome}</th><th style={{ textAlign: "right" }}>Diferença</th></tr></thead><tbody>{ranking.map((row) => <tr key={row.nome}><td>{row.nome}</td><td style={{ textAlign: "right" }}>{formatNumber(row.votosA)}</td><td style={{ textAlign: "right" }}>{formatNumber(row.votosB)}</td><td style={{ textAlign: "right", color: row.votosA - row.votosB >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 700 }}>{row.votosA - row.votosB > 0 ? "+" : ""}{formatNumber(row.votosA - row.votosB)}</td></tr>)}</tbody></table></section><div style={{ marginTop: "1rem" }}><SourceBadge fonte="TSE — Resultados eleitorais 2022" url="https://dadosabertos.tse.jus.br/dataset/resultados-2022" /></div></>}</div>;
}
