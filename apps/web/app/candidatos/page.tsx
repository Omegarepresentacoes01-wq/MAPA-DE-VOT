import Link from "next/link";
import { Users, ArrowRight } from "lucide-react";
import { DEMO_SEARCH_RESULTS } from "@/lib/demo";

export const metadata = { title: "Candidatos" };

export default function CandidatosPage() {
  const candidates = DEMO_SEARCH_RESULTS.filter((item) => item.tipo === "candidato");
  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><Users size={28} style={{ color: "var(--accent)" }} /> Candidatos</h1>
        <p>Explore fichas eleitorais. Enquanto a base oficial não é carregada, esta tela exibe uma amostra local.</p>
      </div>
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {candidates.map((candidate) => (
          <Link key={candidate.id} href={`/candidatos/${candidate.id}`} className="search-result-card">
            <div className="search-result-icon candidato"><Users size={16} /></div>
            <div className="search-result-body"><span className="search-result-title">{candidate.titulo}</span><span className="search-result-sub">{candidate.subtitulo}</span></div>
            <span className="tag">{candidate.uf}</span><ArrowRight size={16} style={{ color: "var(--accent)" }} />
          </Link>
        ))}
      </div>
    </div>
  );
}
