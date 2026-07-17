"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertCircle, FolderOpen, Search, ChevronLeft, ChevronRight, ArrowUpDown, X, CheckSquare, Square } from "lucide-react";
import { DocumentCard } from "@/components/DocumentCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { EmptyState } from "@/components/EmptyState";
import { BatchActionBar } from "@/components/BatchActionBar";

interface Document {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  uploaded_at: string;
}

interface Chunk {
  chunk_id: string;
  content: string;
  source: string;
  page: number;
}

type SortBy = "date" | "name" | "pages";
const PER_PAGE = 10;

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [page, setPage] = useState(1);
  const [chunksDoc, setChunksDoc] = useState<{ doc: Document; chunks: Chunk[] } | null>(null);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

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

  const handleViewChunks = async (doc: Document) => {
    try {
      setLoadingChunks(true);
      const res = await fetch(`/api/documents/${doc.id}/chunks`);
      if (!res.ok) throw new Error("Error al cargar chunks");
      const data = await res.json();
      setChunksDoc({ doc, chunks: data.chunks });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al cargar chunks";
      alert(message);
    } finally {
      setLoadingChunks(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectionMode = () => {
    setSelectionMode((prev) => !prev);
    setSelectedIds(new Set());
  };

  const selectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map((d) => d.id)));
    }
  };

  const handleBatchDelete = async () => {
    const count = selectedIds.size;
    const confirmed = window.confirm(
      `¿Eliminar ${count} archivo(s)?\n\nSe borrarán todos los chunks y archivos PDF asociados.`
    );
    if (!confirmed) return;

    try {
      setBatchDeleting(true);
      const res = await fetch("/api/documents/batch", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_ids: Array.from(selectedIds) }),
      });
      if (!res.ok) throw new Error("Error al eliminar documentos");
      setDocuments((prev) => prev.filter((d) => !selectedIds.has(d.id)));
      setSelectedIds(new Set());
      setSelectionMode(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al eliminar documentos";
      alert(message);
    } finally {
      setBatchDeleting(false);
    }
  };

  const filtered = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "name") return a.filename.localeCompare(b.filename);
    if (sortBy === "pages") return b.pages - a.pages;
    return parseFloat(b.uploaded_at) - parseFloat(a.uploaded_at);
  });

  const totalPages = Math.ceil(sorted.length / PER_PAGE);
  const paged = sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setPage(1);
  };

  const handleSortChange = (value: SortBy) => {
    setSortBy(value);
    setPage(1);
  };

  const sortOptions: { value: SortBy; label: string }[] = [
    { value: "date", label: "Reciente" },
    { value: "name", label: "Nombre" },
    { value: "pages", label: "Paginas" },
  ];

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Documentos</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {filtered.length} de {documents.length} PDF{documents.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={toggleSelectionMode}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              selectionMode
                ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                : "border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            {selectionMode ? (
              <span className="flex items-center gap-1">
                <CheckSquare className="h-4 w-4" />
                Seleccionar
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Square className="h-4 w-4" />
                Seleccionar
              </span>
            )}
          </button>
          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Actualizar
          </button>
        </div>
      </div>

      {!loading && !error && documents.length > 0 && (
        <div className="relative mt-6">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Buscar por nombre..."
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-blue-400"
          />
        </div>
      )}

      {!loading && !error && documents.length > 0 && (
        <div className="mt-4 flex items-center gap-2">
          <ArrowUpDown className="h-4 w-4 text-gray-400 dark:text-gray-500" />
          {sortOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleSortChange(opt.value)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                sortBy === opt.value
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <LoadingSpinner message="Cargando documentos..." />
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500 dark:text-red-400" />
            <div>
              <p className="font-medium text-red-800 dark:text-red-200">Error</p>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
              <button
                onClick={fetchDocuments}
                className="mt-2 text-sm font-medium text-red-600 underline hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
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

      {!loading && paged.length > 0 && (
        <div className="mt-6 space-y-3">
          {selectionMode && (
            <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-800">
              <button
                onClick={selectAll}
                className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
              >
                {selectedIds.size === filtered.length ? "Deseleccionar todo" : "Seleccionar todo"}
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {selectedIds.size} seleccionado(s)
              </span>
            </div>
          )}
          {paged.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={handleDelete}
              onViewChunks={handleViewChunks}
              isDeleting={deletingId === doc.id}
              selected={selectedIds.has(doc.id)}
              onSelect={toggleSelect}
              selectionMode={selectionMode}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg border border-gray-300 p-2 text-gray-600 transition hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Pagina {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="rounded-lg border border-gray-300 p-2 text-gray-600 transition hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {chunksDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl dark:bg-gray-800">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  Chunks: {chunksDoc.doc.filename}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {chunksDoc.chunks.length} chunks indexados
                </p>
              </div>
              <button
                onClick={() => setChunksDoc(null)}
                className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="overflow-y-auto p-4" style={{ maxHeight: "calc(80vh - 60px)" }}>
              {loadingChunks ? (
                <LoadingSpinner message="Cargando chunks..." />
              ) : (
                <div className="space-y-3">
                  {chunksDoc.chunks.map((chunk) => (
                    <div
                      key={chunk.chunk_id}
                      className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                          Pagina {chunk.page}
                        </span>
                        <span className="text-[10px] text-gray-400 dark:text-gray-500">
                          {chunk.chunk_id}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-gray-700 whitespace-pre-wrap dark:text-gray-300">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <BatchActionBar
        selectedCount={selectedIds.size}
        onDelete={handleBatchDelete}
        onClear={() => setSelectedIds(new Set())}
        loading={batchDeleting}
      />
    </div>
  );
}
