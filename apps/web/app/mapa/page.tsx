import type { Metadata } from "next";
import { MapView } from "@/components/map/MapView";

export const metadata: Metadata = {
  title: "Mapa Eleitoral",
  description: "Visualize resultados eleitorais no mapa interativo do Brasil",
};

export default function MapaPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", height: "calc(100dvh - var(--topbar-height) - 4rem)" }}>
      <div className="page-header" style={{ marginBottom: 0 }}>
        <h1>Mapa Eleitoral</h1>
        <p>Resultados por município · Geometrias IBGE 2022 · Fonte: TSE</p>
      </div>
      <MapView />
    </div>
  );
}
