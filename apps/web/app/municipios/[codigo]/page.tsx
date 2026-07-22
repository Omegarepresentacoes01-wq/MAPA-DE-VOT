import Link from "next/link";
import { ArrowLeft, Building2, MapPin, Vote } from "lucide-react";
import { DEMO_MUNICIPALITIES } from "@/lib/demo";

export const metadata = { title: "Município" };

export default async function MunicipioPage({ params }: { params: Promise<{ codigo: string }> }) {
  const { codigo } = await params;
  const municipio = DEMO_MUNICIPALITIES[codigo] || { nome: "Município não cadastrado", uf: "—", populacao: 0, votos_validos: 0 };
  const number = new Intl.NumberFormat("pt-BR");

  return (
    <div>
      <Link href="/mapa" className="btn btn-ghost btn-sm" style={{ marginBottom: "1.5rem" }}><ArrowLeft size={14} /> Voltar ao mapa</Link>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><Building2 size={28} style={{ color: "var(--accent)" }} /> {municipio.nome}</h1>
        <p><MapPin size={14} style={{ verticalAlign: "-2px" }} /> {municipio.uf} · Dados demonstrativos para validação do fluxo local.</p>
      </div>
      <div className="grid-2">
        <div className="stat-card"><div className="stat-label">População estimada</div><div className="stat-value">{municipio.populacao ? number.format(municipio.populacao) : "—"}</div></div>
        <div className="stat-card"><div className="stat-label" style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}><Vote size={14} /> Votos válidos</div><div className="stat-value">{municipio.votos_validos ? number.format(municipio.votos_validos) : "—"}</div></div>
      </div>
    </div>
  );
}
