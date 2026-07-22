import type { Metadata } from "next";
import "./globals.css";
import "./layout.css";
import { PrivateShell } from "@/components/layout/PrivateShell";

export const metadata: Metadata = {
  title: { default: "Mapa de Voto", template: "%s | Mapa de Voto" },
  description:
    "Plataforma de inteligência eleitoral e territorial — dados oficiais TSE e IBGE com rastreabilidade total de fonte.",
  keywords: ["eleições", "TSE", "candidatos", "mapa eleitoral", "dados abertos"],
  openGraph: {
    title: "Mapa de Voto",
    description: "Inteligência eleitoral e territorial com dados oficiais TSE + IBGE",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body><PrivateShell>{children}</PrivateShell></body>
    </html>
  );
}
