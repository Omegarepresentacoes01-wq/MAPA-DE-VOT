"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, ClipboardList, MapPinned, Plus, Target, Users } from "lucide-react";

type Territory = { id: string; municipio: string; uf: string; meta: number; realizado: number; responsavel: string };
type Action = { id: string; text: string; territoryId: string; done: boolean };
type Store = { campaign: string; territories: Territory[]; actions: Action[] };

const KEY = "mapa-voto-command-center-v1";
const emptyStore: Store = { campaign: "Minha campanha", territories: [], actions: [] };
const number = (value: number) => new Intl.NumberFormat("pt-BR").format(value);

export function CommandCenter() {
  const [store, setStore] = useState<Store>(emptyStore);
  const [ready, setReady] = useState(false);
  const [territoryOpen, setTerritoryOpen] = useState(false);
  const [actionOpen, setActionOpen] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(KEY);
    if (saved) {
      try { setStore(JSON.parse(saved)); } catch { window.localStorage.removeItem(KEY); }
    }
    setReady(true);
  }, []);

  useEffect(() => { if (ready) window.localStorage.setItem(KEY, JSON.stringify(store)); }, [ready, store]);

  const summary = useMemo(() => {
    const meta = store.territories.reduce((total, item) => total + item.meta, 0);
    const realizado = store.territories.reduce((total, item) => total + item.realizado, 0);
    return { meta, realizado, gap: Math.max(0, meta - realizado), actions: store.actions.filter((item) => !item.done).length };
  }, [store]);

  function addTerritory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const municipio = String(data.get("municipio") || "").trim();
    const uf = String(data.get("uf") || "").trim().toUpperCase();
    const meta = Number(data.get("meta") || 0);
    const responsavel = String(data.get("responsavel") || "").trim();
    if (!municipio || !uf || meta <= 0) return;
    setStore((current) => ({ ...current, territories: [...current.territories, { id: crypto.randomUUID(), municipio, uf, meta, realizado: 0, responsavel }] }));
    event.currentTarget.reset(); setTerritoryOpen(false);
  }

  function addAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = String(data.get("acao") || "").trim();
    const territoryId = String(data.get("territoryId") || "");
    if (!text) return;
    setStore((current) => ({ ...current, actions: [...current.actions, { id: crypto.randomUUID(), text, territoryId, done: false }] }));
    event.currentTarget.reset(); setActionOpen(false);
  }

  function toggleAction(id: string) { setStore((current) => ({ ...current, actions: current.actions.map((item) => item.id === id ? { ...item, done: !item.done } : item) })); }

  return <div className="command-center">
    <header className="command-header">
      <div><p className="command-eyebrow">OPERAÇÃO ELEITORAL · 2026</p><h1>Comando Central</h1><p>Território, metas e execução da equipe em um só lugar.</p></div>
      <label className="campaign-name">Campanha <input value={store.campaign} onChange={(event) => setStore((current) => ({ ...current, campaign: event.target.value }))} /></label>
    </header>

    <section className="command-alert"><span className="command-alert-dot" /> Base eleitoral oficial ainda não foi importada. Os campos abaixo registram dados operacionais da sua equipe neste navegador.</section>

    <section className="command-metrics">
      <Metric icon={<MapPinned />} label="Territórios ativos" value={store.territories.length} detail="municípios em acompanhamento" />
      <Metric icon={<Target />} label="Meta consolidada" value={number(summary.meta)} detail={summary.meta ? `${number(summary.gap)} votos para a meta` : "cadastre a primeira meta"} />
      <Metric icon={<Users />} label="Responsáveis" value={new Set(store.territories.map((item) => item.responsavel).filter(Boolean)).size} detail="pessoas vinculadas" />
      <Metric icon={<ClipboardList />} label="Ações pendentes" value={summary.actions} detail="itens para execução" />
    </section>

    <section className="command-grid">
      <article className="command-panel command-territories">
        <div className="command-panel-head"><div><h2>Plano territorial</h2><p>Metas por município e responsável de campo.</p></div><button className="command-add" onClick={() => setTerritoryOpen((value) => !value)}><Plus size={16} /> Adicionar território</button></div>
        {territoryOpen && <form className="command-form" onSubmit={addTerritory}>
          <input name="municipio" placeholder="Município" required /> <input name="uf" placeholder="UF" maxLength={2} required /> <input name="meta" type="number" min="1" placeholder="Meta de votos" required /> <input name="responsavel" placeholder="Responsável" /> <button className="btn btn-primary" type="submit">Salvar</button>
        </form>}
        {!store.territories.length ? <Empty icon={<MapPinned />} title="Nenhum território cadastrado" text="Cadastre o primeiro município e defina quem responde por ele." /> : <div className="territory-list">{store.territories.map((item) => { const progress = item.meta ? Math.min(100, item.realizado / item.meta * 100) : 0; return <div className="territory-row" key={item.id}><div className="territory-pin">{item.uf}</div><div className="territory-main"><strong>{item.municipio}</strong><span>{item.responsavel || "Responsável não definido"}</span></div><div className="territory-progress"><span>{number(item.realizado)} / {number(item.meta)}</span><div><i style={{ width: `${progress}%` }} /></div></div><button className="territory-menu" aria-label={`Opções de ${item.municipio}`}><ChevronDown size={16} /></button></div>; })}</div>}
      </article>

      <article className="command-panel command-actions">
        <div className="command-panel-head"><div><h2>Próximas ações</h2><p>O que a equipe precisa executar.</p></div><button className="command-add" onClick={() => setActionOpen((value) => !value)}><Plus size={16} /> Nova ação</button></div>
        {actionOpen && <form className="command-form command-action-form" onSubmit={addAction}><input name="acao" placeholder="Ex.: confirmar agenda da equipe" required /><select name="territoryId"><option value="">Ação geral</option>{store.territories.map((item) => <option key={item.id} value={item.id}>{item.municipio}/{item.uf}</option>)}</select><button className="btn btn-primary" type="submit">Adicionar</button></form>}
        {!store.actions.length ? <Empty icon={<ClipboardList />} title="Sua operação começa aqui" text="Crie uma ação e acompanhe a execução sem planilhas paralelas." /> : <div className="action-list">{store.actions.map((item) => { const territory = store.territories.find((entry) => entry.id === item.territoryId); return <button className={`action-row ${item.done ? "done" : ""}`} key={item.id} onClick={() => toggleAction(item.id)}><span className="action-check">{item.done && <Check size={14} />}</span><span><strong>{item.text}</strong><small>{territory ? `${territory.municipio}/${territory.uf}` : "Ação geral"}</small></span></button>; })}</div>}
      </article>
    </section>
  </div>;
}

function Metric({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string | number; detail: string }) { return <article className="command-metric"><div className="command-metric-icon">{icon}</div><div><p>{label}</p><strong>{value}</strong><span>{detail}</span></div></article>; }
function Empty({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) { return <div className="command-empty"><span>{icon}</span><div><strong>{title}</strong><p>{text}</p></div></div>; }
