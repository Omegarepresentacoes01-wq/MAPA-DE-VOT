"use client";
import { useState } from "react";
import { ArrowLeftRight, TrendingUp, TrendingDown, Minus, AlertCircle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { SourceBadge } from "@/components/shared/SourceBadge";
import { DEMO_COMPARISON_ROWS, DEMO_MODE } from "@/lib/demo";

interface ComparisonRow {
  territory_nome: string;
  votos_a: number | null;
  votos_b: number | null;
  variacao_absoluta: number | null;
  variacao_percentual: number | null;
}

interface Election { id: string; ano: number; turno: number; tipo: string; }

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return new Intl.NumberFormat("pt-BR").format(n);
}

export function Comparador() {
  const [electionA, setElectionA] = useState("");
  const [electionB, setElectionB] = useState("");
  const [codigoIbge, setCodigoIbge] = useState("");
  const [rows, setRows] = useState<ComparisonRow[]>([]);
  const [elA, setElA] = useState<Election | null>(null);
  const [elB, setElB] = useState<Election | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = async () => {
    if (!electionA || !electionB || !codigoIbge) {
      setError("Preencha todos os campos.");
      return;
    }
    setLoading(true);
    setError("");
    if (DEMO_MODE) {
      setRows(DEMO_COMPARISON_ROWS);
      setElA({ id: electionA, ano: 2018, turno: 1, tipo: "Deputado Federal" });
      setElB({ id: electionB, ano: 2022, turno: 1, tipo: "Deputado Federal" });
      setLoading(false);
      return;
    }
    try {
      const params = new URLSearchParams({
        election_a: electionA,
        election_b: electionB,
      });
      const res = await fetch(`/api/v1/territories/${codigoIbge}/compare?${params}`);
      if (!res.ok) throw new Error((await res.json()).detail || "Erro na API");
      const data = await res.json();
      setRows(data.rows || []);
      setElA(data.election_a);
      setElB(data.election_b);
    } catch {
      setRows(DEMO_COMPARISON_ROWS);
      setElA({ id: electionA, ano: 2018, turno: 1, tipo: "Deputado Federal" });
      setElB({ id: electionB, ano: 2022, turno: 1, tipo: "Deputado Federal" });
    } finally {
      setLoading(false);
    }
  };

  const topRows = rows.slice(0, 15);
  const chartData = topRows.map(r => ({
    name: r.territory_nome.split("—")[0].trim(),
    variacao: r.variacao_absoluta || 0,
  }));

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ArrowLeftRight size={28} style={{ color: "var(--accent)" }} />
          Comparador de Eleições
        </h1>
        <p>Compare o desempenho por partido entre duas eleições num mesmo município.</p>
      </div>

      {/* Form */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="grid-3" style={{ marginBottom: "1rem" }}>
          <div>
            <label style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "0.4rem" }}>
              MUNICÍPIO (Código IBGE)
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="Ex: 3550308 (São Paulo)"
              value={codigoIbge}
              onChange={e => setCodigoIbge(e.target.value)}
              maxLength={7}
            />
          </div>
          <div>
            <label style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "0.4rem" }}>
              ELEIÇÃO A (UUID)
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="UUID da eleição mais antiga"
              value={electionA}
              onChange={e => setElectionA(e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "0.4rem" }}>
              ELEIÇÃO B (UUID)
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="UUID da eleição mais recente"
              value={electionB}
              onChange={e => setElectionB(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="badge badge-danger" style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", padding: "0.5rem 0.75rem" }}>
            <AlertCircle size={14} /> {error}
          </div>
        )}

        <button
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={loading}
          id="btn-comparar"
        >
          {loading ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Comparando…</> : <><ArrowLeftRight size={14} /> Comparar</>}
        </button>
      </div>

      {/* Resultados */}
      {rows.length > 0 && (
        <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Cabeçalho */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div className="badge badge-neutral" style={{ fontSize: "var(--text-sm)", padding: "0.5rem 1rem" }}>
              Eleição A: {elA ? `${elA.ano} T${elA.turno} — ${elA.tipo}` : "—"}
            </div>
            <ArrowLeftRight size={16} style={{ color: "var(--text-muted)" }} />
            <div className="badge badge-accent" style={{ fontSize: "var(--text-sm)", padding: "0.5rem 1rem" }}>
              Eleição B: {elB ? `${elB.ano} T${elB.turno} — ${elB.tipo}` : "—"}
            </div>
            <div style={{ marginLeft: "auto" }}>
              <SourceBadge fonte="TSE — Portal de Dados Abertos" url="https://dadosabertos.tse.jus.br" />
            </div>
          </div>

          {/* Gráfico de variação */}
          <div className="card">
            <div className="section-title">Variação de votos por partido (Top 15)</div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ top: 4, right: 16, left: 8, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  angle={-40}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickFormatter={v => fmt(v)} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
                  formatter={(v: any) => [fmt(v), "Variação"]}
                />
                <Bar dataKey="variacao" radius={[4, 4, 0, 0]}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={d.variacao >= 0 ? "var(--success)" : "var(--danger)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Tabela */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Partido</th>
                  <th style={{ textAlign: "right" }}>Eleição A</th>
                  <th style={{ textAlign: "right" }}>Eleição B</th>
                  <th style={{ textAlign: "right" }}>Variação</th>
                  <th style={{ textAlign: "right" }}>%</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const up = (r.variacao_absoluta || 0) > 0;
                  const dn = (r.variacao_absoluta || 0) < 0;
                  return (
                    <tr key={i}>
                      <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {r.territory_nome}
                      </td>
                      <td style={{ textAlign: "right", color: "var(--text-secondary)" }}>{fmt(r.votos_a)}</td>
                      <td style={{ textAlign: "right", color: "var(--text-secondary)" }}>{fmt(r.votos_b)}</td>
                      <td style={{ textAlign: "right", fontWeight: 700, color: up ? "var(--success)" : dn ? "var(--danger)" : "var(--text-muted)" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                          {up ? <TrendingUp size={13} /> : dn ? <TrendingDown size={13} /> : <Minus size={13} />}
                          {fmt(r.variacao_absoluta)}
                        </span>
                      </td>
                      <td style={{ textAlign: "right", color: up ? "var(--success)" : dn ? "var(--danger)" : "var(--text-muted)" }}>
                        {r.variacao_percentual != null ? `${r.variacao_percentual > 0 ? "+" : ""}${r.variacao_percentual.toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
