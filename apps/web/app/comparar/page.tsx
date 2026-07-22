import type { Metadata } from "next";
import { Comparador } from "@/components/compare/Comparador";
export const metadata: Metadata = { title: "Comparador de Eleições" };
export default function CompararPage() {
  return <Comparador />;
}
