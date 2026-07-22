"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, CircleDot, MapPinned, Target, TrendingDown, TrendingUp } from "lucide-react";
import { DEMO_STRATEGY_2026, StrategyPriority } from "@/lib/demo";

const priorityLabel: Record<StrategyPriority, string> = { alta: "Prioridade alta", media: "Prioridade média", manutencao: "Manutenção" };

function number(value: number) { return new Intl.NumberFormat("pt-BR").format(value); }

export function StrategyBoard() {
  const [priority, setPriority] = useState<"todas" | StrategyPriority>("todas");
  const [completed, setCompleted] = useState<string[]>([]);
  const territories = useMemo(
    () => DEMO_STRATEGY_2026.filter((item) => priority === "todas" || item.prioridade === priority),
    [priority],
  );
  const totalMeta = territories.reduce((sum, item) => sum + item.meta, 0);
  const totalPotential = territories.reduce((sum, item) => sum + item.potencial, 0);

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><Target size={28} style={{ color: "var(--accent)" }} /> Estratégia 2026</h1>
        <p>Leitura territorial baseada em eleições anteriores para orientar prioridade, meta e acompanhamento de campo.</p>
      </div>

      <div className="strategy-notice"><MapPinned size={16} /> Dados demonstrativos. Na carga oficial, os indicadores serão calculados com resultados históricos do TSE.</div>

      <div className="grid-3" style={{ margin: "1.25rem 0 1.5rem" }}>
        <div className="stat-card"><div className="stat-label">Territórios prioritários</div><div className="stat-value">{territories.length}</div><div className="stat-sub">Seleção atual</div></div>
        <div className="stat-card"><div className="stat-label">Meta de votos</div><div className="stat-value">{number(totalMeta)}</div><div className="stat-sub">Soma das metas territoriais</div></div>
        <div className="stat-card"><div className="stat-label">Potencial mapeado</div><div className="stat-value">{number(totalPotential)}</div><div className="stat-sub">Referência de planejamento</div></div>
      </div>

      <section className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div className="strategy-toolbar">
          <div><div className="section-title" style={{ marginBottom: ".25rem" }}>Plano territorial</div><p>Classifique, acompanhe e ajuste o plano por município.</p></div>
          <div className="strategy-filter" role="group" aria-label="Filtrar prioridade">
            {(["todas", "alta", "media"] as const).map((item) => <button key={item} className={`btn btn-sm ${priority === item ? "btn-primary" : "btn-ghost"}`} onClick={() => setPriority(item)}>{item === "todas" ? "Todas" : priorityLabel[item]}</button>)}
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table strategy-table">
            <thead><tr><th>Município</th><th>Prioridade</th><th style={{ textAlign: "right" }}>2022</th><th style={{ textAlign: "right" }}>Última eleição</th><th style={{ textAlign: "right" }}>Variação</th><th style={{ textAlign: "right" }}>Meta 2026</th><th>Próxima ação</th><th /></tr></thead>
            <tbody>{territories.map((item) => {
              const positive = item.variacao >= 0;
              const done = completed.includes(item.codigo);
              return <tr key={item.codigo}>
                <td><strong>{item.municipio}</strong><span className="strategy-sub">{item.uf} · potencial {number(item.potencial)}</span></td>
                <td><span className={`badge strategy-priority ${item.prioridade}`}>{priorityLabel[item.prioridade]}</span></td>
                <td style={{ textAlign: "right" }}>{number(item.votos2022)}</td>
                <td style={{ textAlign: "right" }}>{number(item.votos2024)}</td>
                <td style={{ textAlign: "right", color: positive ? "var(--success)" : "var(--danger)", fontWeight: 700 }}>{positive ? <TrendingUp size={13} /> : <TrendingDown size={13} />} {positive ? "+" : ""}{item.variacao.toFixed(1)}%</td>
                <td style={{ textAlign: "right", fontWeight: 700 }}>{number(item.meta)}</td>
                <td><span className="strategy-action">{item.status}</span></td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => setCompleted((current) => done ? current.filter((code) => code !== item.codigo) : [...current, item.codigo])}>{done ? <><CheckCircle2 size={14} /> Revisado</> : <><CircleDot size={14} /> Revisar</>}</button></td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
