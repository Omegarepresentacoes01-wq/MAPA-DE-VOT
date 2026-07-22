import type { Metadata } from "next";
export const metadata: Metadata = { title: "Exportações" };

import { ExportPanel } from "@/components/export/ExportPanel";
export default function ExportarPage() {
  return <ExportPanel />;
}
