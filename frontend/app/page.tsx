import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          Pidiefs
        </h1>
        <p className="mt-3 text-lg text-gray-500">
          PDF Knowledge Base — RAG Pipeline
        </p>
        <p className="mt-2 text-sm text-gray-400">
          Sube tus PDFs, genera embeddings y consulta tu conocimiento con IA
        </p>
      </div>

      <div className="mt-12 grid gap-6 sm:grid-cols-2">
        <Link
          href="/upload"
          className="group rounded-xl border border-gray-200 bg-white p-8 shadow-sm transition hover:shadow-md"
        >
          <div className="text-2xl">&#128196;</div>
          <h2 className="mt-3 font-semibold text-gray-900">Subir PDFs</h2>
          <p className="mt-1 text-sm text-gray-500">
            Extrae texto, genera embeddings y almacena en la base vectorial
          </p>
        </Link>

        <Link
          href="/chat"
          className="group rounded-xl border border-gray-200 bg-white p-8 shadow-sm transition hover:shadow-md"
        >
          <div className="text-2xl">&#128172;</div>
          <h2 className="mt-3 font-semibold text-gray-900">Consultar</h2>
          <p className="mt-1 text-sm text-gray-500">
            Haz preguntas sobre tus documentos y recibe respuestas con fuentes
          </p>
        </Link>
      </div>

      <div className="mt-16 rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="font-semibold text-gray-900">Stack</h3>
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
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
