"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="es">
      <body className="min-h-screen flex flex-col items-center justify-center bg-gray-50 text-gray-900">
        <div className="rounded-xl border border-red-200 bg-red-50 p-8 max-w-md text-center">
          <h2 className="text-lg font-semibold text-red-800">
            Error critico
          </h2>
          <p className="mt-2 text-sm text-red-600">
            {error.message || "Ocurrio un error inesperado en la aplicacion"}
          </p>
          <button
            onClick={reset}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      </body>
    </html>
  );
}
