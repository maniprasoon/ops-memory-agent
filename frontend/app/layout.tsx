import type { Metadata } from "next";
import { RoutePreloader } from "@/components/route-preloader";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ops Memory Agent",
  description: "A memory-backed operations assistant."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <RoutePreloader />
        {children}
      </body>
    </html>
  );
}
