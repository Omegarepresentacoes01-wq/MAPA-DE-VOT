"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, MapPinned, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { formatNumber, loadOfficialDataset, OfficialDataset } from "@/components/local/official-data";

export function OfficialCandidateDetail({ id }: { id: string }) {
  const [dataset, setDataset] = useState<OfficialDataset | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { loadOfficialDataset().then(setDataset).catch((cause) => setError(cause.message)); }, []);
  const candidate = dataset?.candidates.find((item) => item.id === id);
  const municipalities = useMemo(() => dataset ? dataset.mapa.features.map((feature) => ({ nome: feature.properties.nome, votos: feature.properties.votos[id] || 0, total: feature.properties.total })).filter((item) => item.votos > 0).sort((a, b) => b.votos - a.votos) : [], [dataset, id]);
  return <div><Link href="/candidatos" className="btn btn-ghost btn-sm" style={{ marginBottom: "1.5rem" }}><ArrowLeft size={14} /> Voltar aos candidatos</Link>
    {error ? <div className="card"><AlertCircle color="var(--warning)" /> {error}</div> : !dataset ? <div className="card">Carregando resultado oficial…</div> : !candidate ? <div className="card">Esta candidatura não existe na base oficial importada.</div> : <><div className="page-header"><h1 style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><Users size={28} style={{ color: "var(--accent)" }} /> {candidate.nome}</h1><p>Governador · Rondônia · 1º turno de 2022 · TSE</p></div><div className="grid-2" style={{ marginBottom: "1.5rem" }}><div className="stat-card"><div className="stat-label">Votos no estado</div><div className="stat-value">{formatNumber(candidate.votos)}</div><div className="stat-sub">Resultado agregado oficial</div></div><div className="stat-card"><div className="stat-label">Municípios com votos</div><div className="stat-value">{municipalities.length}</div><div className="stat-sub">No recorte importado</div></div></div><section className="card" style={{ padding: 0, overflow: "hidden" }}><div className="section-title" style={{ padding: "1rem" }}><MapPinned size={17} /> Municípios com maior votação</div><table className="data-table"><thead><tr><th>Município</th><th style={{ textAlign: "right" }}>Votos</th><th style={{ textAlign: "right" }}>% dos válidos locais</th></tr></thead><tbody>{municipalities.slice(0, 15).map((item) => <tr key={item.nome}><td>{item.nome}</td><td style={{ textAlign: "right" }}>{formatNumber(item.votos)}</td><td style={{ textAlign: "right" }}>{item.total ? `${((item.votos / item.total) * 100).toFixed(1)}%` : "—"}</td></tr>)}</tbody></table></section></>}</div>;
}
