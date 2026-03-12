import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "./globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LogosGotham | Tactical Logistics Intelligence",
  description: "Military-grade Logistics Disruption Intelligence System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${geistMono.variable} antialiased`}>
        <div className="crt-overlay" />
        <main className="relative w-screen h-screen overflow-hidden bg-[#050505] text-white">
          {children}
        </main>
      </body>
    </html>
  );
}
