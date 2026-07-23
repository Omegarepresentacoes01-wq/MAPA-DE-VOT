import Link from "next/link";

export const metadata = { title: "Município" };

export default async function MunicipioPage({ params }: { params: Promise<{ codigo: string }> }) {
  const { codigo } = await params;
  return <div><div className="page-header"><h1>Município</h1><p>Consulta territorial oficial.</p></div><div className="card"><p>Não há dados complementares cadastrados para o código <strong>{codigo}</strong>. A votação oficial está disponível diretamente no mapa.</p><Link className="btn btn-primary" href="/mapa">Abrir mapa eleitoral</Link></div></div>;
}
