"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertCircle, FolderOpen, Search } from "lucide-react";
import { DocumentCard } from "@/components/DocumentCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { EmptyState } from "@/components/EmptyState";

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
  const [searchTerm, setSearchTerm] = useState("");

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/documents");
      if (!res.ok) throw new Error("Error al cargar documentos");
      const data = await res.json();
      setDocuments(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error de conexion con el backend";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDelete = async (doc: Document) => {
    const confirmed = window.confirm(
      `Eliminar "${doc.filename}"?\n\nSe borraran ${doc.chunks} chunks y el archivo PDF.`
    );
    if (!confirmed) return;

    try {
      setDeletingId(doc.id);
      const res = await fetch(`/api/documents/${doc.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Error al eliminar");
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al eliminar el documento";
      alert(message);
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos</h1>
          <p className="mt-1 text-sm text-gray-500">
            {filtered.length} de {documents.length} PDF{documents.length !== 1 ? "s" : ""}
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

      {!loading && !error && documents.length > 0 && (
        <div className="relative mt-6">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por nombre..."
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {loading && (
        <LoadingSpinner message="Cargando documentos..." />
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
        <EmptyState
          icon={FolderOpen}
          title="No hay documentos"
          description="Sube un PDF para comenzar"
        />
      )}

      {!loading && !error && documents.length > 0 && filtered.length === 0 && (
        <EmptyState
          icon={Search}
          title="Sin resultados"
          description={`No se encontraron documentos para "${searchTerm}"`}
        />
      )}

      {!loading && filtered.length > 0 && (
        <div className="mt-6 space-y-3">
          {filtered.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={handleDelete}
              isDeleting={deletingId === doc.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
