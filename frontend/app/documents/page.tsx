"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Trash2,
  Loader2,
  AlertCircle,
  FolderOpen,
} from "lucide-react";

interface Document {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  uploaded_at: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://localhost:8000/api/documents");
      if (!res.ok) throw new Error("Error al cargar documentos");
      const data = await res.json();
      setDocuments(data);
    } catch (err: any) {
      setError(err.message || "Error de conexion con el backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (doc: Document) => {
    const confirmed = window.confirm(
      `Eliminar "${doc.filename}"?\n\nSe borraran ${doc.chunks} chunks y el archivo PDF.`
    );
    if (!confirmed) return;

    try {
      setDeletingId(doc.id);
      const res = await fetch(
        `http://localhost:8000/api/documents/${doc.id}`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error("Error al eliminar");
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err: any) {
      alert(err.message || "Error al eliminar el documento");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (ts: string) => {
    const d = new Date(parseFloat(ts) * 1000);
    return d.toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos</h1>
          <p className="mt-1 text-sm text-gray-500">
            {documents.length} PDF{documents.length !== 1 ? "s" : ""} subidos
          </p>
        </div>
        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
        >
          Actualizar
        </button>
      </div>

      {loading && (
        <div className="mt-12 flex flex-col items-center justify-center text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-3 text-sm text-gray-500">Cargando documentos...</p>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Error</p>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              <button
                onClick={fetchDocuments}
                className="mt-2 text-sm font-medium text-red-600 underline hover:text-red-800"
              >
                Reintentar
              </button>
            </div>
          </div>
        </div>
      )}

      {!loading && !error && documents.length === 0 && (
        <div className="mt-12 flex flex-col items-center justify-center text-center">
          <FolderOpen className="h-12 w-12 text-gray-300" />
          <p className="mt-4 text-lg font-medium text-gray-400">
            No hay documentos
          </p>
          <p className="mt-1 text-sm text-gray-300">
            Sube un PDF para comenzar
          </p>
        </div>
      )}

      {!loading && documents.length > 0 && (
        <div className="mt-6 space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md"
            >
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500" />
                <div>
                  <p className="font-medium text-gray-900">{doc.filename}</p>
                  <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-gray-500">
                    <span>
                      {doc.pages} pagina{doc.pages !== 1 ? "s" : ""}
                    </span>
                    <span>
                      {doc.chunks} chunk{doc.chunks !== 1 ? "s" : ""}
                    </span>
                    <span>{formatDate(doc.uploaded_at)}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-gray-300">ID: {doc.id}</p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc)}
                disabled={deletingId === doc.id}
                className="flex-shrink-0 rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                title="Eliminar documento"
              >
                {deletingId === doc.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
