export type OfficialDataset = {
  meta: { fonte: string; cargo: string; turno: number; uf: string };
  candidates: Array<{ id: string; nome: string; votos: number }>;
  mapa: {
    type: "FeatureCollection";
    features: Array<{
      type: "Feature";
      geometry: unknown;
      properties: { codigo_ibge: string; nome: string; total: number; votos: Record<string, number> };
    }>;
  };
};

export const formatNumber = (value: number) => new Intl.NumberFormat("pt-BR").format(value);

export async function loadOfficialDataset(): Promise<OfficialDataset> {
  const response = await fetch("/api/local/elections/2022/ro");
  if (!response.ok) throw new Error("A base oficial do TSE ainda não foi importada neste computador.");
  return response.json();
}
