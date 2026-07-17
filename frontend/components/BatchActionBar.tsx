"use client";

import { Trash2, X } from "lucide-react";

interface BatchActionBarProps {
  selectedCount: number;
  onDelete: () => void;
  onClear: () => void;
  loading?: boolean;
}

export function BatchActionBar({ selectedCount, onDelete, onClear, loading }: BatchActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white px-4 py-3 shadow-lg dark:border-gray-700 dark:bg-gray-900">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {selectedCount} archivo(s) seleccionado(s)
          </span>
          <button
            onClick={onClear}
            className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-gray-500 transition hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <X className="h-3 w-3" />
            Deseleccionar
          </button>
        </div>
        <button
          onClick={onDelete}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          {loading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
          Eliminar {selectedCount} archivo(s)
        </button>
      </div>
    </div>
  );
}
