"use client";
import { useState } from "react";
import Link from "next/link";
import {
  User, TrendingUp, DollarSign, MapPin, Calendar,
  Award, ChevronRight, Vote, BarChart3, AlertCircle
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import { SourceBadge } from "@/components/shared/SourceBadge";
import "./ficha360.css";

interface CandidacyDetail {
  candidatura: Record<string, any>;
  historico_eleitoral: any[];
  financas: Record<string, any>;
  votos_por_municipio: any[];
  meta?: { fonte: string; url?: string };
}

const PIE_COLORS = [
  "hsl(217,91%,60%)", "hsl(142,71%,45%)", "hsl(38,92%,55%)",
  "hsl(280,80%,65%)", "hsl(0,72%,55%)", "hsl(199,89%,48%)",
  "hsl(340,82%,58%)", "hsl(60,80%,50%)",
];

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return new Intl.NumberFormat("pt-BR").format(n);
}
function fmtMoney(n: number | null | undefined) {
  if (n == null) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
}
function fmtDate(s?: string) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("pt-BR"); } catch { return s; }
}

function situacaoBadge(sit?: string) {
  if (!sit) return null;
  const s = sit.toUpperCase();
  if (s.includes("ELEITO") && !s.includes("NÃO")) return { label: "Eleito ✓", cls: "badge-success" };
  if (s.includes("SUPLENTE")) return { label: "Suplente", cls: "badge-info" };
  if (s.includes("CASSAD") || s.includes("INDEFERID")) return { label: "Cassado", cls: "badge-danger" };
  if (s.includes("NÃO ELEITO") || s.includes("NAO ELEITO")) return { label: "Não eleito", cls: "badge-neutral" };
  return { label: sit, cls: "badge-neutral" };
}

const TABS = ["Resumo", "Histórico", "Finanças", "Votos"];

export function Ficha360({ data }: { data: CandidacyDetail }) {
  const [tab, setTab] = useState(0);
  const { candidatura: c, historico_eleitoral, financas, votos_por_municipio, meta } = data;
  const sit = situacaoBadge(c.situacao);

  return (
    <div className="ficha360 fade-in">
      {/* ── Hero ── */}
      <div className="ficha360-hero">
        <div className="ficha360-avatar">
          {(c.nome_urna || c.nome || "?").slice(0, 2).toUpperCase()}
        </div>
        <div className="ficha360-hero-info">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <h1 className="ficha360-nome">{c.nome_urna || c.nome}</h1>
            {sit && <span className={`badge ${sit.cls}`} style={{ fontSize: "0.75rem" }}>{sit.label}</span>}
          </div>
          <div className="ficha360-meta-row">
            {c.partido_sigla && (
              <span className="tag" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
                {c.partido_sigla}
              </span>
            )}
            {c.cargo_descricao && <span className="tag">{c.cargo_descricao}</span>}
            {c.territorio_uf && <span className="tag"><MapPin size={10} /> {c.territorio_uf}</span>}
            {c.numero_urna && <span className="tag">Nº {c.numero_urna}</span>}
          </div>
          {meta && <SourceBadge fonte={meta.fonte} url={meta.url} />}
        </div>
        {c.votos_totais && (
          <div className="ficha360-hero-votes">
            <div className="stat-label">Total de Votos</div>
            <div className="stat-value" style={{ fontSize: "2rem" }}>{fmt(c.votos_totais)}</div>
          </div>
        )}
      </div>

      {/* ── Tabs ── */}
      <div className="tabs" style={{ marginBottom: "1.5rem" }}>
        {TABS.map((t, i) => (
          <button key={t} className={`tab ${tab === i ? "active" : ""}`} onClick={() => setTab(i)}>
            {t}
          </button>
        ))}
      </div>

      {/* ── Tab: Resumo ── */}
      {tab === 0 && (
        <div className="fade-in">
          <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
            <InfoCard icon={<User size={16} />} label="Nome completo" value={c.nome} />
            <InfoCard icon={<Calendar size={16} />} label="Nascimento" value={fmtDate(c.nascimento)} />
            <InfoCard icon={<Award size={16} />} label="Escolaridade" value={c.escolaridade} />
            <InfoCard icon={<User size={16} />} label="Gênero" value={c.genero} />
            <InfoCard icon={<User size={16} />} label="Raça/Cor" value={c.raca_cor} />
            <InfoCard icon={<TrendingUp size={16} />} label="Ocupação" value={c.ocupacao} />
            <InfoCard icon={<MapPin size={16} />} label="Município" value={c.territorio_nome} />
            <InfoCard icon={<DollarSign size={16} />} label="Bens declarados" value={fmtMoney(c.bens_declarados)} />
          </div>
        </div>
      )}

      {/* ── Tab: Histórico ── */}
      {tab === 1 && (
        <div className="fade-in">
          {historico_eleitoral.length === 0 ? (
            <div className="empty-state">
              <Vote size={32} />
              <h3>Nenhum histórico anterior encontrado</h3>
              <p>Esta é a primeira candidatura registrada para este candidato.</p>
            </div>
          ) : (
            <div className="ficha360-timeline">
              {historico_eleitoral.map((h: any, i: number) => {
                const hSit = situacaoBadge(h.situacao);
                return (
                  <div key={i} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="timeline-card card">
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <strong style={{ color: "var(--text-primary)" }}>{h.eleicao}</strong>
                        {hSit && <span className={`badge ${hSit.cls}`}>{hSit.label}</span>}
                      </div>
                      <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        <span className="tag">{h.cargo}</span>
                        <span className="tag" style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>
                          {h.partido}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Finanças ── */}
      {tab === 2 && (
        <div className="fade-in">
          <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-card">
              <div className="stat-label">Total de Receitas</div>
              <div className="stat-value" style={{ color: "var(--success)" }}>
                {fmtMoney(financas.total_receitas)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total de Despesas</div>
              <div className="stat-value" style={{ color: "var(--danger)" }}>
                {fmtMoney(financas.total_despesas)}
              </div>
            </div>
          </div>

          <div className="grid-2">
            {/* Receitas por origem */}
            {financas.receitas_por_origem?.length > 0 && (
              <div className="card">
                <div className="section-title" style={{ fontSize: "var(--text-sm)" }}>
                  <DollarSign size={14} style={{ color: "var(--success)" }} /> Receitas por Origem
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={financas.receitas_por_origem}
                      dataKey="total"
                      nameKey="origem"
                      cx="50%" cy="50%"
                      outerRadius={80}
                      label={({ origem, percent }) =>
                        `${(origem || "").slice(0, 12)}: ${(percent * 100).toFixed(0)}%`
                      }
                      labelLine={false}
                    >
                      {financas.receitas_por_origem.map((_: any, i: number) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
                      formatter={(v: any) => fmtMoney(v)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Despesas por categoria */}
            {financas.despesas_por_categoria?.length > 0 && (
              <div className="card">
                <div className="section-title" style={{ fontSize: "var(--text-sm)" }}>
                  <BarChart3 size={14} style={{ color: "var(--danger)" }} /> Despesas por Categoria
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={financas.despesas_por_categoria} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis type="number" tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickFormatter={v => `R$${(v/1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="categoria" tick={{ fill: "var(--text-muted)", fontSize: 10 }} width={90} />
                    <Tooltip
                      contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
                      formatter={(v: any) => fmtMoney(v)}
                    />
                    <Bar dataKey="total" fill="var(--danger)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {financas.total_receitas == null && (
            <div className="empty-state">
              <AlertCircle size={32} />
              <h3>Dados de finanças não disponíveis</h3>
              <p>As prestações de contas desta candidatura ainda não foram ingeridas.</p>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Votos ── */}
      {tab === 3 && (
        <div className="fade-in">
          {votos_por_municipio.length === 0 ? (
            <div className="empty-state">
              <BarChart3 size={32} />
              <h3>Distribuição de votos não disponível</h3>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Município</th>
                    <th>Código IBGE</th>
                    <th style={{ textAlign: "right" }}>Votos</th>
                  </tr>
                </thead>
                <tbody>
                  {votos_por_municipio.map((v: any, i: number) => (
                    <tr key={i}>
                      <td style={{ color: "var(--text-muted)" }}>{i + 1}</td>
                      <td>
                        <Link href={`/municipios/${v.codigo_ibge}`} style={{ color: "var(--accent)", fontWeight: 500 }}>
                          {v.nome}
                        </Link>
                      </td>
                      <td><span className="tag">{v.codigo_ibge}</span></td>
                      <td style={{ textAlign: "right", fontWeight: 700, color: "var(--text-primary)" }}>
                        {fmt(v.votos)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value?: any }) {
  return (
    <div className="stat-card">
      <div className="stat-label" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
        <span style={{ color: "var(--accent)", opacity: 0.7 }}>{icon}</span>
        {label}
      </div>
      <div style={{ marginTop: "0.4rem", fontSize: "var(--text-sm)", fontWeight: 500, color: "var(--text-primary)" }}>
        {value || <span style={{ color: "var(--text-muted)" }}>—</span>}
      </div>
    </div>
  );
}
