"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";

export function PrivateShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <>{children}</>;
  return <div className="app-shell"><Sidebar /><div className="app-main"><main className="app-content">{children}</main></div></div>;
}
