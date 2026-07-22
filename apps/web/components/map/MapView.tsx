"use client";

import { useEffect, useRef, useState } from "react";
import { BarChart3, Check, ChevronDown, Layers3, Map, Minus, Plus, RotateCcw, Search, SlidersHorizontal, Target } from "lucide-react";
import "./map-view.css";

const controls = [
  { id: "busca", label: "Busca", icon: Search },
  { id: "analise", label: "Análise", icon: BarChart3 },
  { id: "camadas", label: "Camadas", icon: Layers3 },
];

type ElectionDataset = {
  meta: { fonte: string; cargo: string; turno: number; uf: string };
  candidates: Array<{ id: string; nome: string; votos: number }>;
  mapa: { type: "FeatureCollection"; features: Array<{ type: "Feature"; geometry: unknown; properties: { codigo_ibge: string; nome: string; total: number; votos: Record<string, number> } }> };
};

const number = (value: number) => new Intl.NumberFormat("pt-BR").format(value);

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const [dataset, setDataset] = useState<ElectionDataset | null>(null);
  const [candidateId, setCandidateId] = useState("");
  const [datasetError, setDatasetError] = useState("");
  const [activeControl, setActiveControl] = useState("busca");
  const [year, setYear] = useState("2022");
  const [uf, setUf] = useState("RO");
  const [office, setOffice] = useState("Governador");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    import("maplibre-gl").then(({ default: maplibregl }) => {
      import("maplibre-gl/dist/maplibre-gl.css");
      const map = new maplibregl.Map({
        container: mapRef.current!,
        style: {
          version: 8,
          glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
          sources: { osm: { type: "raster", tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap" } },
          layers: [{ id: "background", type: "background", paint: { "background-color": "#12171d" } }, { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": .68, "raster-saturation": -1, "raster-contrast": .25, "raster-brightness-max": .42, "raster-hue-rotate": 185 } }],
        },
        center: [-63.9, -10.9], zoom: 5.25, minZoom: 3, maxZoom: 16, attributionControl: false,
      });
      map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
      map.on("load", () => { setLoading(false); setMapReady(true); });
      mapInstanceRef.current = map;
    });
    return () => { mapInstanceRef.current?.remove(); mapInstanceRef.current = null; };
  }, []);

  useEffect(() => {
    fetch("/api/local/elections/2022/ro").then(async (response) => {
      if (!response.ok) throw new Error();
      const source = await response.json() as ElectionDataset;
      setDataset(source);
      setCandidateId(source.candidates[0]?.id || "");
    }).catch(() => setDatasetError("Importe a base oficial local para ativar o mapa."));
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!mapReady || !map || !dataset || !candidateId) return;
    const featured = { ...dataset.mapa, features: dataset.mapa.features.map((feature) => ({ ...feature, properties: { ...feature.properties, votos_candidato: feature.properties.votos[candidateId] || 0 } })) };
    if (map.getSource("resultado-tse")) {
      map.getSource("resultado-tse").setData(featured);
      return;
    }
    map.addSource("resultado-tse", { type: "geojson", data: featured });
    map.addLayer({ id: "resultado-tse-fill", type: "fill", source: "resultado-tse", paint: { "fill-color": ["interpolate", ["linear"], ["get", "votos_candidato"], 0, "#14202b", 250, "#1d4ed8", 1500, "#2563eb", 6000, "#22c55e", 15000, "#84cc16", 35000, "#facc15"], "fill-opacity": .82 } });
    map.addLayer({ id: "resultado-tse-line", type: "line", source: "resultado-tse", paint: { "line-color": "#9bb5c6", "line-width": .65, "line-opacity": .7 } });
    map.fitBounds([[-66.9, -13.9], [-59.8, -7.7]], { padding: { left: 310, right: 410, top: 110, bottom: 100 }, duration: 700 });
  }, [candidateId, dataset, mapReady]);

  const reset = () => mapInstanceRef.current?.flyTo({ center: [-63.9, -10.9], zoom: 5.25, duration: 650 });

  return <div className="electoral-map-shell">
    <div ref={mapRef} className="electoral-map-canvas" aria-label="Mapa eleitoral do Brasil" />
    {loading && <div className="map-load-state"><span /><strong>Preparando mapa eleitoral</strong></div>}

    <aside className="map-insight-rail">
      <div className="map-rail-title"><Target size={18} /><div><strong>Leitura territorial</strong><span>Base oficial ainda não importada</span></div></div>
      <p>Quando os resultados do TSE forem carregados, esta área mostrará redutos, evolução e oportunidades por município.</p>
      <div className="map-rail-grid">
        <button><span>01</span><strong>Onde foi mais forte</strong><small>Ranking de municípios</small></button>
        <button><span>02</span><strong>Onde perdeu força</strong><small>Comparação entre ciclos</small></button>
        <button><span>03</span><strong>Meta por território</strong><small>Planejamento de campo</small></button>
        <button><span>04</span><strong>Comparar candidatos</strong><small>Sobreposição eleitoral</small></button>
      </div>
      <div className="map-rail-empty"><Map size={20} /><span>Importe o resultado eleitoral para ativar a análise territorial.</span></div>
    </aside>

    <div className="map-toolbar">{controls.map(({ id, label, icon: Icon }) => <button key={id} className={activeControl === id ? "active" : ""} onClick={() => setActiveControl(id)}><Icon size={16} />{label}</button>)}<span /><button aria-label="Aproximar" onClick={() => mapInstanceRef.current?.zoomIn()}><Plus size={17} /></button><button aria-label="Afastar" onClick={() => mapInstanceRef.current?.zoomOut()}><Minus size={17} /></button></div>

    <aside className="map-query-panel">
      <header><div><h1>Mapa Eleitoral</h1><p>Consulta territorial por resultado oficial.</p></div><button onClick={() => setQuery("")} aria-label="Limpar busca">×</button></header>
      <div className="map-query-form">
        <label>Ano<select value={year} onChange={(event) => setYear(event.target.value)}><option>2022</option><option>2024</option></select></label>
        <label>UF<select value={uf} onChange={(event) => setUf(event.target.value)}><option>RO</option></select></label>
        <label>Cargo<select value={office} onChange={(event) => setOffice(event.target.value)}><option>Governador</option><option>Presidente</option><option>Senador</option><option>Deputado Federal</option></select></label>
        <label>Turno<select><option>1º Turno</option><option>2º Turno</option></select></label>
      </div>
      <div className="map-search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar candidato ou município" /></div>
      {dataset ? <section className="map-data-state map-data-loaded"><div><Check size={18} /><strong>Resultado oficial carregado</strong></div><p>{dataset.meta.fonte} · {dataset.meta.cargo} · {dataset.meta.turno}º turno · {dataset.meta.uf}</p><label className="map-candidate-select">Candidato<select value={candidateId} onChange={(event) => setCandidateId(event.target.value)}>{dataset.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.nome} — {number(candidate.votos)} votos</option>)}</select></label><div className="map-candidate-ranking">{dataset.candidates.slice(0, 3).map((candidate, index) => <button key={candidate.id} onClick={() => setCandidateId(candidate.id)} className={candidate.id === candidateId ? "selected" : ""}><b>{index + 1}</b><span>{candidate.nome}</span><small>{number(candidate.votos)}</small></button>)}</div></section> : <section className="map-data-state"><div><Layers3 size={18} /><strong>Nenhum resultado carregado</strong></div><p>{datasetError || "Importe uma base oficial do TSE para colorir o mapa e calcular os indicadores."}</p><button onClick={() => window.location.assign("/exportar")}><SlidersHorizontal size={15} /> Ver importações</button></section>}
      <div className="map-accordion"><span><BarChart3 size={16} /> Resumo de desempenho</span><ChevronDown size={16} /></div>
      <div className="map-accordion"><span><Map size={16} /> Camadas territoriais</span><ChevronDown size={16} /></div>
      <div className="map-accordion"><span><Target size={16} /> Estratégia e metas</span><ChevronDown size={16} /></div>
    </aside>
    <div className="map-legend"><strong>Votos por município</strong><span><i /> {dataset ? "Resultado TSE 2022 · RO" : "Aguardando base oficial TSE"}</span></div>
    <div className="map-actions"><button onClick={reset}><RotateCcw size={15} /> Centralizar</button><button><Check size={15} /> Configurações</button></div>
  </div>;
}
