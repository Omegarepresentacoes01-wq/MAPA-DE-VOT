import type { Metadata } from "next";
import { CommandCenter } from "@/components/command/CommandCenter";

export const metadata: Metadata = {
  title: "Comando Central | Mapa de Voto",
  description: "Operação territorial e eleitoral da equipe",
};

export default function HomePage() { return <CommandCenter />; }
