"use client";

import { useEffect, useRef, useState } from "react";
import { BarChart3, Check, ChevronDown, Layers3, Map, Minus, Plus, RotateCcw, Search, SlidersHorizontal, Target } from "lucide-react";
import "./map-view.css";

const controls = [
  { id: "busca", label: "Busca", icon: Search },
  { id: "analise", label: "Análise", icon: BarChart3 },
  { id: "camadas", label: "Camadas", icon: Layers3 },
];

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
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
      map.on("load", () => setLoading(false));
      mapInstanceRef.current = map;
    });
    return () => { mapInstanceRef.current?.remove(); mapInstanceRef.current = null; };
  }, []);

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
        <label>UF<select value={uf} onChange={(event) => setUf(event.target.value)}><option>RO</option><option>SP</option><option>RJ</option></select></label>
        <label>Cargo<select value={office} onChange={(event) => setOffice(event.target.value)}><option>Governador</option><option>Presidente</option><option>Senador</option><option>Deputado Federal</option></select></label>
        <label>Turno<select><option>1º Turno</option><option>2º Turno</option></select></label>
      </div>
      <div className="map-search-input"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar candidato ou município" /></div>
      <section className="map-data-state"><div><Layers3 size={18} /><strong>Nenhum resultado carregado</strong></div><p>Importe uma base oficial do TSE para colorir o mapa e calcular os indicadores.</p><button onClick={() => window.location.assign("/exportar")}><SlidersHorizontal size={15} /> Ver importações</button></section>
      <div className="map-accordion"><span><BarChart3 size={16} /> Resumo de desempenho</span><ChevronDown size={16} /></div>
      <div className="map-accordion"><span><Map size={16} /> Camadas territoriais</span><ChevronDown size={16} /></div>
      <div className="map-accordion"><span><Target size={16} /> Estratégia e metas</span><ChevronDown size={16} /></div>
    </aside>
    <div className="map-legend"><strong>Resultados eleitorais</strong><span><i /> Aguardando base oficial TSE</span></div>
    <div className="map-actions"><button onClick={reset}><RotateCcw size={15} /> Centralizar</button><button><Check size={15} /> Configurações</button></div>
  </div>;
}
