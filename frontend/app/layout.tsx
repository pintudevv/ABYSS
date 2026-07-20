import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/src/providers";

export const metadata: Metadata = {
  title: "ABYSS — Hybrid ML Malware Sandbox & Deception",
  description: "Semester project malware instrumentation, analysis, and forensics panel.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased dark" suppressHydrationWarning>
      <body className="min-h-screen bg-[#070709] text-zinc-100 flex flex-col justify-between selection:bg-[#FF2E55] selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
