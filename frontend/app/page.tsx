"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { FileText, BookOpen, Layers, Clock, Loader2, Upload, MessageSquare } from "lucide-react";
import ModeInfoSection from "@/components/ModeInfoSection";

interface Stats {
  total_documents: number;
  total_pages: number;
  total_chunks: number;
  last_upload: string | null;
}

function formatLastUpload(ts: string | null): string {
  if (!ts) return "Nunca";
  const d = new Date(parseFloat(ts) * 1000);
  return d.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/documents/stats")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => setError("No se pudo conectar con el backend"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          Pidiefs
        </h1>
        <p className="mt-3 text-lg text-gray-500 dark:text-gray-400">
          PDF Knowledge Base — RAG Pipeline
        </p>
        <p className="mt-2 text-sm text-gray-400 dark:text-gray-500">
          Sube tus PDFs, genera embeddings y consulta tu conocimiento con IA
        </p>
      </div>

      {loading ? (
        <div className="mt-12 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="mt-12 rounded-xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 text-sm font-medium text-red-600 underline hover:text-red-700 dark:text-red-400"
          >
            Reintentar
          </button>
        </div>
      ) : stats && (
        <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <FileText className="mx-auto h-6 w-6 text-blue-500 dark:text-blue-400" />
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
              {stats.total_documents}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Documento{stats.total_documents !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <BookOpen className="mx-auto h-6 w-6 text-green-500 dark:text-green-400" />
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
              {stats.total_pages}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Pagina{stats.total_pages !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <Layers className="mx-auto h-6 w-6 text-purple-500 dark:text-purple-400" />
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
              {stats.total_chunks}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Chunk{stats.total_chunks !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <Clock className="mx-auto h-6 w-6 text-orange-500 dark:text-orange-400" />
            <p className="mt-2 text-sm font-bold text-gray-900 dark:text-gray-100">
              {formatLastUpload(stats.last_upload)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Ultimo upload
            </p>
          </div>
        </div>
      )}

      <div className="mt-12 grid gap-6 sm:grid-cols-2">
        <Link
          href="/upload"
          className="group rounded-xl border-2 border-gray-300 bg-white p-8 transition hover:border-blue-400 hover:bg-blue-50 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-blue-500 dark:hover:bg-blue-900/20"
        >
          <div className="flex justify-center">
            <Upload className="h-8 w-8 text-blue-500 dark:text-blue-400" />
          </div>
          <h2 className="mt-3 font-semibold text-gray-900 dark:text-gray-100">Subir PDFs</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Extrae texto, genera embeddings y almacena en la base vectorial
          </p>
        </Link>

        <Link
          href="/chat"
          className="group rounded-xl border-2 border-gray-300 bg-white p-8 transition hover:border-blue-400 hover:bg-blue-50 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-blue-500 dark:hover:bg-blue-900/20"
        >
          <div className="flex justify-center">
            <MessageSquare className="h-8 w-8 text-blue-500 dark:text-blue-400" />
          </div>
          <h2 className="mt-3 font-semibold text-gray-900 dark:text-gray-100">Consultar</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Haz preguntas sobre tus documentos y recibe respuestas con fuentes
          </p>
        </Link>
      </div>

      <ModeInfoSection />

      <div className="mt-16 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Stack</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            "Next.js",
            "FastAPI",
            "LangChain",
            "Sentence Transformers",
            "ChromaDB",
            "Groq (Llama 3.3 70B)",
            "SQLite",
          ].map((tech) => (
            <span
              key={tech}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
