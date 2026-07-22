"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Download, Map, Target, Users, Vote } from "lucide-react";

const sections = [
  { title: "INTELIGÊNCIA ELEITORAL", items: [{ href: "/mapa", icon: Map, label: "Mapas eleitorais" }, { href: "/candidatos", icon: BarChart3, label: "Votações" }] },
  { title: "OPERAÇÃO DE CAMPANHA", items: [{ href: "/estrategia", icon: Target, label: "Planejador territorial" }, { href: "/comparar", icon: Users, label: "Lideranças" }, { href: "/exportar", icon: Download, label: "Relatórios" }] },
];

export function Sidebar() {
  const pathname = usePathname() || "";

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  }

  return (
    <aside className="sidebar">
      <Link href="/" className="sidebar-logo">
        <div className="sidebar-logo-icon"><Vote size={17} /></div>
        <div>
          <span className="sidebar-logo-text">Mapa de Voto</span>
          <span className="sidebar-logo-sub">INTELIGÊNCIA ELEITORAL</span>
        </div>
      </Link>
      <nav className="sidebar-nav">
        <Link href="/" className={`nav-item command-link ${pathname === "/" ? "active" : ""}`}><span className="command-pulse">⌁</span>Comando Central<span className="command-score">{pathname === "/" ? "—" : ""}</span></Link>
        {sections.map((section) => <div className="sidebar-group" key={section.title}><span className="sidebar-section-label">{section.title}</span>{section.items.map(({ href, icon: Icon, label }) => { const active = pathname === href || pathname.startsWith(`${href}/`); return <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}><Icon size={17} />{label}</Link>; })}</div>)}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-account"><span>OA</span><div><strong>Equipe interna</strong><small>Ambiente local</small></div></div>
        <button className="sidebar-logout" onClick={logout}>Sair do sistema</button>
      </div>
    </aside>
  );
}
