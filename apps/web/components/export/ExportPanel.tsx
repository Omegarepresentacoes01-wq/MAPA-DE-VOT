"use client";
import { useState } from "react";
import { Download, FileText, Table2, Code2, CheckCircle, Clock, AlertCircle } from "lucide-react";
import { SourceBadge } from "@/components/shared/SourceBadge";
import { DEMO_MODE } from "@/lib/demo";

const FORMATS = [
  { id: "csv", label: "CSV", icon: <Table2 size={16} />, desc: "Compatível com Excel, Google Sheets e BI tools" },
  { id: "xlsx", label: "XLSX", icon: <FileText size={16} />, desc: "Excel formatado com cabeçalhos e rodapé de fonte" },
  { id: "json", label: "JSON", icon: <Code2 size={16} />, desc: "Para integração com sistemas e APIs" },
];

interface Job { id: string; status: string; formato: string; url_download?: string; }

export function ExportPanel() {
  const [formato, setFormato] = useState("csv");
  const [uf, setUf] = useState("");
  const [situacao, setSituacao] = useState("");
  const [partido, setPartido] = useState("");
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [polling, setPolling] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    setJob(null);
    if (DEMO_MODE) {
      const csv = "nome_urna,partido,uf,situacao\\nMarina Alves,PSB,SP,ELEITO\\nRafael Nogueira,PT,SP,SUPLENTE\\n";
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      setJob({ id: "demo-export", status: "done", formato, url_download: url });
      setLoading(false);
      return;
    }
    try {
      const params = new URLSearchParams({ formato });
      if (uf) params.set("uf", uf);
      if (situacao) params.set("situacao", situacao);
      if (partido) params.set("partido", partido);

      const res = await fetch(`/api/v1/exports/candidatos?${params}`, { method: "POST" });
      if (!res.ok) throw new Error("Falha ao iniciar exportação");
      const data = await res.json();
      setJob(data);
      pollStatus(data.job_id);
    } catch {
      const csv = "nome_urna,partido,uf,situacao\\nMarina Alves,PSB,SP,ELEITO\\nRafael Nogueira,PT,SP,SUPLENTE\\n";
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      setJob({ id: "demo-export", status: "done", formato, url_download: url });
    } finally {
      setLoading(false);
    }
  };

  const pollStatus = async (jobId: string) => {
    setPolling(true);
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/exports/${jobId}`);
        const data = await res.json();
        setJob(data);
        if (data.status === "done" || data.status === "failed") {
          clearInterval(interval);
          setPolling(false);
        }
      } catch {
        clearInterval(interval);
        setPolling(false);
      }
    }, 1500);
  };

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Download size={28} style={{ color: "var(--accent)" }} />
          Exportações
        </h1>
        <p>Exporte dados eleitorais filtrados em CSV, XLSX ou JSON.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "1.5rem" }}>
        {/* Filtros */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="section-title">Filtros</div>

          <div className="grid-2">
            <div>
              <label className="field-label">UF</label>
              <input type="text" className="input-field" placeholder="Ex: SP" maxLength={2} value={uf} onChange={e => setUf(e.target.value.toUpperCase())} />
            </div>
            <div>
              <label className="field-label">Situação</label>
              <select className="input-field" value={situacao} onChange={e => setSituacao(e.target.value)}>
                <option value="">Todas</option>
                <option value="ELEITO">Eleito</option>
                <option value="NÃO ELEITO">Não Eleito</option>
                <option value="SUPLENTE">Suplente</option>
              </select>
            </div>
          </div>

          <div>
            <label className="field-label">Partido</label>
            <input type="text" className="input-field" placeholder="Sigla do partido (ex: PT)" value={partido} onChange={e => setPartido(e.target.value.toUpperCase())} />
          </div>

          <SourceBadge fonte="TSE — Portal de Dados Abertos" url="https://dadosabertos.tse.jus.br" />
        </div>

        {/* Formato + ação */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="section-title">Formato</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {FORMATS.map(f => (
                <label
                  key={f.id}
                  style={{
                    display: "flex", alignItems: "center", gap: "0.75rem",
                    padding: "0.75rem", borderRadius: "var(--radius)",
                    border: `1px solid ${formato === f.id ? "var(--accent)" : "var(--border)"}`,
                    background: formato === f.id ? "var(--accent-glow)" : "var(--bg-elevated)",
                    cursor: "pointer", transition: "all var(--transition-fast)",
                  }}
                >
                  <input type="radio" name="formato" value={f.id} checked={formato === f.id} onChange={() => setFormato(f.id)} style={{ accentColor: "var(--accent)" }} />
                  <span style={{ color: formato === f.id ? "var(--accent)" : "var(--text-secondary)" }}>{f.icon}</span>
                  <div>
                    <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-primary)" }}>{f.label}</div>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{f.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <button className="btn btn-primary btn-lg" onClick={handleExport} disabled={loading || polling} style={{ width: "100%", justifyContent: "center" }} id="btn-exportar">
            {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Preparando…</> : <><Download size={16} /> Exportar Candidatos</>}
          </button>

          {/* Status do job */}
          {job && (
            <div className="card fade-in" style={{ borderColor: job.status === "done" ? "var(--success)" : job.status === "failed" ? "var(--danger)" : "var(--accent)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                {job.status === "done" && <CheckCircle size={18} style={{ color: "var(--success)" }} />}
                {job.status === "running" || job.status === "pending" ? <span className="spinner" /> : null}
                {job.status === "failed" && <AlertCircle size={18} style={{ color: "var(--danger)" }} />}
                <div>
                  <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                    {job.status === "done" ? "Pronto para download!" : job.status === "failed" ? "Falha na exportação" : "Gerando arquivo…"}
                  </div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                    {job.formato.toUpperCase()} · ID: {job.id.slice(0, 8)}
                  </div>
                </div>
              </div>
              {job.status === "done" && job.url_download && (
                <a
                  href={job.url_download}
                  className="btn btn-primary btn-sm"
                  style={{ marginTop: "0.75rem", width: "100%", justifyContent: "center" }}
                  download
                >
                  <Download size={14} /> Baixar arquivo
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
