import type { Metadata } from "next";
import { Suspense } from "react";
import { SearchHero } from "@/components/search/SearchHero";
import { SearchResults } from "@/components/search/SearchResults";
import { RecentStats } from "@/components/search/RecentStats";

export const metadata: Metadata = {
  title: "Busca | Mapa de Voto",
  description: "Busque candidatos, municípios e partidos nos dados eleitorais do TSE",
};

export default function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; tipo?: string; page?: string }>;
}) {
  return (
    <div>
      <SearchHero />
      <Suspense fallback={<div className="skeleton" style={{ height: 200, marginTop: "2rem" }} />}>
        <SearchResultsWrapper searchParams={searchParams} />
      </Suspense>
      <RecentStats />
    </div>
  );
}

async function SearchResultsWrapper({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; tipo?: string; page?: string }>;
}) {
  const params = await searchParams;
  if (!params.q) return null;
  return <SearchResults query={params.q} tipo={params.tipo} page={Number(params.page) || 1} />;
}
