import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Ficha360 } from "@/components/candidate/Ficha360";
import { DEMO_CANDIDATE } from "@/lib/demo";

const API = process.env.INTERNAL_API_URL || "http://api:8000";

async function getCandidate(id: string) {
  if (process.env.DEMO_MODE !== "false") return DEMO_CANDIDATE;
  try {
    const res = await fetch(`${API}/api/v1/candidates/${id}`, { next: { revalidate: 300 } });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("API error");
    return res.json();
  } catch {
    return DEMO_CANDIDATE;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const data = await getCandidate(id);
  if (!data) return { title: "Candidato não encontrado" };
  const nome = data.candidatura?.nome_urna || data.candidatura?.nome || "Candidato";
  const partido = data.candidatura?.partido_sigla || "";
  const cargo = data.candidatura?.cargo_descricao || "";
  return {
    title: `${nome} — ${partido} · ${cargo}`,
    description: `Ficha 360 de ${nome}: histórico eleitoral, finanças de campanha e distribuição de votos.`,
  };
}

export default async function CandidatePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await getCandidate(id);
  if (!data) notFound();

  return (
    <div>
      {/* Back */}
      <Link href="/" className="btn btn-ghost btn-sm" style={{ marginBottom: "1.5rem" }}>
        <ArrowLeft size={14} /> Voltar à busca
      </Link>

      <Ficha360 data={data} />
    </div>
  );
}
