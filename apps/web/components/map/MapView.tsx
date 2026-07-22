"use client";
import { useEffect, useRef, useState } from "react";
import { Layers, ZoomIn, ZoomOut, RotateCcw, Info } from "lucide-react";
import "./map-view.css";

const LAYERS = [
  { id: "municipios", label: "Municípios", color: "var(--accent)" },
  { id: "setores", label: "Setores Censitários", color: "var(--success)" },
  { id: "locais", label: "Locais de Votação", color: "var(--warning)" },
];

const ELECTIONS = [
  { id: "", label: "Selecione uma eleição…" },
  { id: "2022-1", label: "2022 — 1º Turno · Presidente" },
  { id: "2022-1-gov", label: "2022 — 1º Turno · Governador" },
];

export function MapView() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [activeLayer, setActiveLayer] = useState("municipios");
  const [election, setElection] = useState("");
  const [hovered, setHovered] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // MapLibre é client-only
    import("maplibre-gl").then(({ default: maplibregl }) => {
      import("maplibre-gl/dist/maplibre-gl.css");

      const map = new maplibregl.Map({
        container: mapRef.current!,
        style: {
          version: 8,
          glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [
            { id: "background", type: "background", paint: { "background-color": "#f8fafc" } },
            {
              id: "osm",
              type: "raster",
              source: "osm-tiles",
              paint: { "raster-opacity": 0.45, "raster-saturation": -0.4 },
            },
          ],
        },
        center: [-51.9253, -14.235],  // Centro do Brasil
        zoom: 4,
        minZoom: 3,
        maxZoom: 16,
        attributionControl: false,
      });

      map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");

      map.on("load", () => {
        setLoading(false);

        // Camada de municípios via MVT (pg_tileserv)
        map.addSource("municipios", {
          type: "vector",
          tiles: ["/api/v1/maps/tiles/public.territory/{z}/{x}/{y}.mvt"],
          minzoom: 3,
          maxzoom: 10,
        });

        map.addLayer({
          id: "municipios-fill",
          type: "fill",
          source: "municipios",
          "source-layer": "territory",
          paint: {
            "fill-color": "hsla(217,91%,60%,0.15)",
            "fill-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.5, 8, 0.8],
          },
        });

        map.addLayer({
          id: "municipios-line",
          type: "line",
          source: "municipios",
          "source-layer": "territory",
          paint: {
            "line-color": "hsla(217,91%,60%,0.5)",
            "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.3, 8, 0.8, 12, 1.5],
          },
        });

        map.addLayer({
          id: "municipios-hover",
          type: "fill",
          source: "municipios",
          "source-layer": "territory",
          paint: { "fill-color": "hsla(217,91%,60%,0.4)" },
          filter: ["==", "nome", ""],
        });

        // Hover
        let hoveredId: any = null;
        map.on("mousemove", "municipios-fill", (e) => {
          if (!e.features?.length) return;
          const props = e.features[0].properties;
          setHovered(props);
          if (hoveredId !== null) {
            map.setFilter("municipios-hover", ["==", "nome", ""]);
          }
          hoveredId = props?.nome;
          map.setFilter("municipios-hover", ["==", "nome", hoveredId]);
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "municipios-fill", () => {
          setHovered(null);
          hoveredId = null;
          map.setFilter("municipios-hover", ["==", "nome", ""]);
          map.getCanvas().style.cursor = "";
        });

        // Click → navega para ficha do município
        map.on("click", "municipios-fill", (e) => {
          if (!e.features?.length) return;
          const { codigo_ibge } = e.features[0].properties as any;
          if (codigo_ibge) window.open(`/municipios/${codigo_ibge}`, "_blank");
        });
      });

      mapInstanceRef.current = map;
    });

    return () => {
      mapInstanceRef.current?.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  const flyToCenter = () => {
    mapInstanceRef.current?.flyTo({ center: [-51.9253, -14.235], zoom: 4, duration: 1000 });
  };

  return (
    <div className="map-wrapper">
      {/* Controles */}
      <div className="map-controls">
        {/* Layer selector */}
        <div className="map-panel">
          <div className="map-panel-title"><Layers size={13} /> Camadas</div>
          {LAYERS.map(l => (
            <label key={l.id} className="map-layer-item">
              <input
                type="radio"
                name="layer"
                value={l.id}
                checked={activeLayer === l.id}
                onChange={() => setActiveLayer(l.id)}
              />
              <span className="map-layer-dot" style={{ background: l.color }} />
              {l.label}
            </label>
          ))}
        </div>

        {/* Eleição */}
        <div className="map-panel">
          <div className="map-panel-title"><Info size={13} /> Colorir por eleição</div>
          <select
            className="input-field"
            value={election}
            onChange={e => setElection(e.target.value)}
            style={{ fontSize: "var(--text-xs)", padding: "0.4rem 0.6rem" }}
          >
            {ELECTIONS.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}
          </select>
        </div>

        {/* Zoom */}
        <div className="map-zoom-btns">
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => mapInstanceRef.current?.zoomIn()} title="Zoom in" aria-label="Zoom in"><ZoomIn size={14} /></button>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => mapInstanceRef.current?.zoomOut()} title="Zoom out" aria-label="Zoom out"><ZoomOut size={14} /></button>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={flyToCenter} title="Centralizar" aria-label="Centralizar mapa"><RotateCcw size={14} /></button>
        </div>
      </div>

      {/* Tooltip hover */}
      {hovered && (
        <div className="map-tooltip">
          <strong>{hovered.nome}</strong>
          <span className="tag" style={{ marginTop: "0.25rem" }}>{hovered.uf}</span>
          {hovered.populacao && <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Pop: {Number(hovered.populacao).toLocaleString("pt-BR")}</span>}
          <span style={{ fontSize: "var(--text-xs)", color: "var(--accent)", marginTop: "0.25rem" }}>Clique para ver ficha →</span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="map-loading">
          <div className="spinner" />
          <span>Carregando mapa…</span>
        </div>
      )}

      {/* Mapa */}
      <div ref={mapRef} className="map-container" aria-label="Mapa eleitoral interativo do Brasil" />
    </div>
  );
}
