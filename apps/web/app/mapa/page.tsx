import type { Metadata } from "next";
import { MapView } from "@/components/map/MapView";

export const metadata: Metadata = {
  title: "Mapa Eleitoral",
  description: "Visualize resultados eleitorais no mapa interativo do Brasil",
};

export default function MapaPage() {
  return <MapView />;
}
