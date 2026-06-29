import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StealthOS — Hybrid ML Malware Sandbox & Deception",
  description: "Semester project malware instrumentation, analysis, and forensics panel.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-screen bg-[#050508] text-gray-100 flex flex-col justify-between">
        {children}
      </body>
    </html>
  );
}
