import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pidiefs — PDF Knowledge Base",
  description: "Consulta tus documentos PDF con RAG y embeddings",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gray-50 text-gray-900">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
            <Link href="/" className="text-lg font-bold tracking-tight">
              Pidiefs
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/" className="hover:text-blue-600 transition-colors">
                Inicio
              </Link>
              <Link
                href="/upload"
                className="hover:text-blue-600 transition-colors"
              >
                Subir PDF
              </Link>
              <Link
                href="/documents"
                className="hover:text-blue-600 transition-colors"
              >
                Documentos
              </Link>
              <Link
                href="/chat"
                className="hover:text-blue-600 transition-colors"
              >
                Consultar
              </Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
