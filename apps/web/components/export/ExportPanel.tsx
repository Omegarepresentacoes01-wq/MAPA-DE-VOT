"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Download } from "lucide-react";
import { formatNumber, loadOfficialDataset, OfficialDataset } from "@/components/local/official-data";

export function ExportPanel() {
  const [dataset, setDataset] = useState<OfficialDataset | null>(null);
  const [error, setError] = useState("");
  const [format, setFormat] = useState<"csv" | "json">("csv");
  useEffect(() => { loadOfficialDataset().then(setDataset).catch((cause) => setError(cause.message)); }, []);
  const download = () => {
    if (!dataset) return;
    const records = dataset.candidates.map((candidate) => ({ candidato: candidate.nome, votos_estado: candidate.votos, ano: 2022, uf: "RO", cargo: "Governador", turno: 1, fonte: dataset.meta.fonte }));
    const body = format === "json" ? JSON.stringify(records, null, 2) : ["candidato;votos_estado;ano;uf;cargo;turno;fonte", ...records.map((row) => `${row.candidato};${row.votos_estado};${row.ano};${row.uf};${row.cargo};${row.turno};${row.fonte}`)].join("\n");
    const blob = new Blob([body], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `tse-ro-governador-2022.${format}`; anchor.click(); URL.revokeObjectURL(url);
  };
  return <div><div className="page-header"><h1 style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><Download size={28} style={{ color: "var(--accent)" }} /> Exportações</h1><p>Baixe somente a base oficial disponível neste computador.</p></div>{error ? <div className="card"><AlertCircle color="var(--warning)" /> {error}</div> : !dataset ? <div className="card">Carregando base oficial…</div> : <div className="card" style={{ maxWidth: 680 }}><div style={{ display: "flex", alignItems: "center", gap: ".65rem", marginBottom: "1rem" }}><CheckCircle2 color="var(--success)" /><strong>Resultado oficial carregado</strong></div><p style={{ color: "var(--text-secondary)" }}>{dataset.meta.fonte} · {dataset.candidates.length} candidaturas · {formatNumber(dataset.mapa.features.length)} municípios.</p><label className="field-label" style={{ marginTop: "1rem" }}>Formato<select className="input-field" value={format} onChange={(event) => setFormat(event.target.value as "csv" | "json")}><option value="csv">CSV</option><option value="json">JSON</option></select></label><button id="btn-exportar" className="btn btn-primary btn-lg" style={{ marginTop: "1rem" }} onClick={download}><Download size={16} /> Baixar resultados oficiais</button></div>}</div>;
}
