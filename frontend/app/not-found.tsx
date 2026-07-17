import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <FileQuestion className="h-16 w-16 text-gray-300 dark:text-gray-600" />
      <h2 className="mt-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
        Pagina no encontrada
      </h2>
      <p className="mt-2 text-gray-500 dark:text-gray-400">
        La pagina que buscas no existe.
      </p>
      <Link
        href="/"
        className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
      >
        Volver al inicio
      </Link>
    </div>
  );
}
