import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TraceGrade",
  description: "Turn production AI agent failures into regression tests",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        <nav className="border-b border-[var(--border)] px-6 py-3 flex items-center gap-6">
          <a href="/" className="text-lg font-bold tracking-tight">
            TraceGrade
          </a>
          <a href="/sessions" className="text-sm text-[var(--muted)] hover:text-[var(--fg)]">
            Sessions
          </a>
          <a href="/evals" className="text-sm text-[var(--muted)] hover:text-[var(--fg)]">
            Evals
          </a>
          <a href="/runs" className="text-sm text-[var(--muted)] hover:text-[var(--fg)]">
            Runs
          </a>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
