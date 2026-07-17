import { FileText, Trash2, Loader2 } from "lucide-react";

interface Document {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  uploaded_at: string;
}

interface DocumentCardProps {
  document: Document;
  onDelete: (doc: Document) => void;
  isDeleting: boolean;
}

function formatDate(ts: string) {
  const d = new Date(parseFloat(ts) * 1000);
  return d.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function DocumentCard({ document: doc, onDelete, isDeleting }: DocumentCardProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:shadow-lg dark:hover:shadow-gray-900/20">
      <div className="flex items-start gap-3">
        <FileText className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500 dark:text-blue-400" />
        <div>
          <p className="font-medium text-gray-900 dark:text-gray-100">{doc.filename}</p>
          <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-gray-500 dark:text-gray-400">
            <span>
              {doc.pages} pagina{doc.pages !== 1 ? "s" : ""}
            </span>
            <span>
              {doc.chunks} chunk{doc.chunks !== 1 ? "s" : ""}
            </span>
            <span>{formatDate(doc.uploaded_at)}</span>
          </div>
          <p className="mt-1 text-[10px] text-gray-300 dark:text-gray-600">ID: {doc.id}</p>
        </div>
      </div>
      <button
        onClick={() => onDelete(doc)}
        disabled={isDeleting}
        className="flex-shrink-0 rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-900/20 dark:hover:text-red-400"
        title="Eliminar documento"
      >
        {isDeleting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4" />
        )}
      </button>
    </div>
  );
}
