import { Users, Vote, Globe, Database } from "lucide-react";
import { SourceBadge } from "@/components/shared/SourceBadge";

const STATS = [
  { icon: <Users size={20} />, label: "Candidaturas", value: "575 mil+", sub: "Eleições 2022", color: "var(--accent)" },
  { icon: <Vote size={20} />, label: "Votos computados", value: "123,6 mi", sub: "Eleições 2022", color: "var(--success)" },
  { icon: <Globe size={20} />, label: "Municípios", value: "5.570", sub: "Com geometria IBGE", color: "var(--warning)" },
  { icon: <Database size={20} />, label: "Fontes oficiais", value: "TSE + IBGE", sub: "Dados abertos", color: "var(--info)" },
];

export function RecentStats() {
  return (
    <section style={{ marginTop: "3rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--text-primary)" }}>
          Cobertura da plataforma
        </h2>
        <SourceBadge
          fonte="TSE + IBGE — Dados oficiais"
          url="https://dadosabertos.tse.jus.br"
        />
      </div>

      <div className="grid-4">
        {STATS.map(({ icon, label, value, sub, color }) => (
          <div
            key={label}
            className="stat-card"
            style={{ borderTop: `3px solid ${color}`, paddingTop: "1.25rem" }}
          >
            <div style={{ color, marginBottom: "0.75rem", opacity: 0.8 }}>{icon}</div>
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ fontSize: "1.5rem", color }}>{value}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
