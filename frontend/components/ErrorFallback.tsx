"use client";

import { AlertCircle } from "lucide-react";

interface ErrorFallbackProps {
  error: Error;
  reset: () => void;
}

export function ErrorFallback({ error, reset }: ErrorFallbackProps) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
      <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-8 dark:border-red-800 dark:bg-red-900/20">
        <AlertCircle className="mx-auto h-10 w-10 text-red-400 dark:text-red-500" />
        <h2 className="mt-4 text-lg font-semibold text-red-800 dark:text-red-200">
          Algo salio mal
        </h2>
        <p className="mt-2 text-sm text-red-600 dark:text-red-300">
          {error.message || "Ocurrio un error inesperado"}
        </p>
        <button
          onClick={reset}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    </div>
  );
}
