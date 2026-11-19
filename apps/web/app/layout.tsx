import type { Metadata } from "next";
import { Provider } from "@/lib/context";
import "./globals.css";
export const metadata: Metadata = {
  title: "ARCAMBE GeoAnalytics",
  description:
    "Análise espectral e cartografia ambiental com Sentinel-2 e Landsat 8/9.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
