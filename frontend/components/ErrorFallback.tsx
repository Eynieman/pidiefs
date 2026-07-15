"use client";

import { AlertCircle } from "lucide-react";

interface ErrorFallbackProps {
  error: Error;
  reset: () => void;
}

export function ErrorFallback({ error, reset }: ErrorFallbackProps) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
      <div className="rounded-xl border border-red-200 bg-red-50 p-8 max-w-md">
        <AlertCircle className="mx-auto h-10 w-10 text-red-400" />
        <h2 className="mt-4 text-lg font-semibold text-red-800">
          Algo salio mal
        </h2>
        <p className="mt-2 text-sm text-red-600">
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
