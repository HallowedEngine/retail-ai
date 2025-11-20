import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RetailAI - Akıllı Stok Yönetim Sistemi",
  description: "Fiş tarama, OCR, stok yönetimi ve SKT uyarı sistemi",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="antialiased bg-gray-50">
        {children}
      </body>
    </html>
  );
}
