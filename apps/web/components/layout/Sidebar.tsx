"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, Map, Users, ArrowLeftRight, Download, Vote, ChevronRight } from "lucide-react";

const navItems = [
  { href: "/", icon: Search, label: "Busca" },
  { href: "/mapa", icon: Map, label: "Mapa Eleitoral" },
  { href: "/candidatos", icon: Users, label: "Candidatos" },
  { href: "/comparar", icon: ArrowLeftRight, label: "Comparador" },
  { href: "/exportar", icon: Download, label: "Exportações" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      {/* Logo */}
      <Link href="/" className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Vote size={18} color="white" />
        </div>
        <div>
          <span className="sidebar-logo-text">Mapa de Voto</span>
          <span className="sidebar-logo-sub">Inteligência Eleitoral</span>
        </div>
      </Link>

      {/* Nav */}
      <nav className="sidebar-nav">
        <span className="sidebar-section-label">Plataforma</span>
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
              <Icon size={16} />
              {label}
              {active && <ChevronRight size={12} style={{ marginLeft: "auto", opacity: 0.6 }} />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <p className="sidebar-version">v0.1.0 · Dados TSE + IBGE</p>
      </div>
    </aside>
  );
}
