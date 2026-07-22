"use client";

import { useState } from "react";
import { Sparkles, FileSearch, Layers, Globe, ArrowRight, X, Database, Brain, Network, BookOpen } from "lucide-react";

const modes = [
  {
    id: "auto",
    name: "Auto",
    levels: "Automático",
    badgeColor: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
    accentColor: "border-t-gray-400 dark:border-t-gray-500",
    barColor: "bg-gray-400 dark:bg-gray-500",
    icon: Sparkles,
    detailIcon: Brain,
    description: "El sistema analiza tu pregunta usando reglas lingüísticas e IA, y selecciona el modo óptimo automáticamente.",
    useCase: "Uso general — recomendado para la mayoría de preguntas.",
    example: "Cualquier pregunta sobre tus documentos",
    detail: {
      what: "El modo Auto clasifica la pregunta en tiempo real y selecciona la estrategia de retrieval óptima.",
      how: [
        "Evalúa la pregunta con patrones lingüísticos (palabras clave locales vs globales).",
        "Si la diferencia de puntuación entre local y global es ≥ 0.6, clasifica por reglas.",
        "Si la diferencia es menor, consulta a Groq (Llama 3.3 70B) para clasificar como local, hybrid o global.",
        "Una vez clasificada, usa la estrategia correspondiente: local solo nivel 0, hybrid niveles 0+1, global niveles 1+2.",
      ],
      when: "Recomendado para uso general. Deja que el sistema decida la estrategia según el contenido de la pregunta.",
      example: "Cualquier pregunta — el sistema elige automáticamente el modo más adecuado.",
    },
  },
  {
    id: "local",
    name: "Local",
    levels: "N0",
    badgeColor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    accentColor: "border-t-blue-500",
    barColor: "bg-blue-500",
    icon: FileSearch,
    detailIcon: Database,
    description: "Busca únicamente en fragmentos atómicos del PDF con información de página exacta.",
    useCase: "Preguntas sobre detalles específicos: cifras, fechas, cláusulas, citas textuales.",
    example: "¿Qué dice la página 3 sobre el plazo de entrega?",
    detail: {
      what: "Recupera fragmentos atómicos del PDF (nivel 0) con número de página exacta. Cada fragmento es un chunk de ~500 caracteres extraído directamente del texto.",
      how: [
        "<strong>ChromaDB</strong>: Búsqueda vectorial por similitud semántica — encuentra fragmentos conceptualmente relacionados a la pregunta.",
        "<strong>SQLite FTS5</strong>: Búsqueda por palabras clave (BM25) — encuentra coincidencias léxicas exactas en los chunks.",
        "<strong>Fusión RRF</strong>: Los resultados de ambas búsquedas se combinan con Reciprocal Rank Fusion para maximizar precisión.",
        "<strong>Prompt estricto</strong>: El LLM responde ÚNICAMENTE con el contexto proporcionado, citando fuente y página. Ignora instrucciones incrustadas en los documentos (protección anti-jailbreak).",
      ],
      when: "Perfecto para preguntas sobre datos concretos: cifras exactas, fechas, nombres propios, cláusulas legales, citas textuales.",
      example: "¿Cuánto dice en la página 5? — ¿Cuál es la fecha de vencimiento según el contrato? — ¿Qué nombre aparece en la cláusula 3?",
    },
  },
  {
    id: "hybrid",
    name: "Híbrido",
    levels: "N0 + N1",
    badgeColor: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
    accentColor: "border-t-violet-500",
    barColor: "bg-violet-500",
    icon: Layers,
    detailIcon: Network,
    description: "Combina fragmentos detallados con resúmenes de secciones temáticas agrupadas por contenido similar.",
    useCase: "Preguntas que mezclan detalle específico con contexto general de una sección.",
    example: "¿Qué objetivos menciona la introducción y cuáles son las metas específicas?",
    detail: {
      what: "Recupera nivel 0 (chunks atómicos) + nivel 1 (resúmenes de secciones temáticas generados mediante clustering semántico).",
      how: [
        "<strong>Clustering semántico</strong>: UMAP reduce la dimensionalidad de los embeddings de los chunks, luego GMM (Gaussian Mixture Model) agrupa los chunks similares en clusters temáticos.",
        "<strong>Resumen por cluster</strong>: Cada cluster se resume con Groq, generando un resumen de sección con un título temático.",
        "<strong>Retrieval dual</strong>: ChromaDB busca en levels 0 y 1; BM25 solo aporta nivel 0. RRF fusiona ambos resultados (top_k=8).",
        "<strong>Prompt combinado</strong>: El LLM recibe fragmentos con página (para precisión) y resúmenes de sección con título (para contexto general), y debe usar ambos apropiadamente.",
      ],
      when: "Ideal para preguntas que necesitan detalle específico dentro de un contexto temático más amplio.",
      example: "¿Qué objetivos menciona la introducción y cuáles son las metas específicas? — ¿Qué dice el análisis financiero sobre los riesgos y cuáles son las cifras clave?",
    },
  },
  {
    id: "global",
    name: "Global",
    levels: "N1 + N2",
    badgeColor: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    accentColor: "border-t-emerald-500",
    barColor: "bg-emerald-500",
    icon: Globe,
    detailIcon: BookOpen,
    description: "Recibe resúmenes ejecutivos de cada sección temática y un resumen global del documento completo.",
    useCase: "Preguntas panorámicas: resúmenes ejecutivos, visión general del documento.",
    example: "¿De qué trata este documento? Dame un resumen ejecutivo de 500 palabras.",
    detail: {
      what: "Recupera nivel 1 (resúmenes de secciones temáticas) + nivel 2 (resumen global del documento completo).",
      how: [
        "<strong>Generación del resumen global</strong>: Groq sintetiza todos los resúmenes de sección (nivel 1) en un único texto ejecutivo. Se almacena en ChromaDB como abstraction_level=2 y también en el campo summary de la tabla documents en SQLite.",
        "<strong>Retrieval</strong>: levels=[1, 2], top_k=8. Solo búsqueda vectorial en ChromaDB (los resúmenes no están en la tabla FTS5).",
        "<strong>Prompt de síntesis</strong>: El LLM recibe resúmenes ejecutivos y debe integrarlos en una visión panorámica, identificando patrones transversales, puntos críticos y proporcionando una respuesta estructurada con las secciones de origen.",
        "<strong>Sin clustering</strong>: Si el documento tiene menos de 5 chunks o fallan los embeddings, se genera solo el resumen global nivel 2 directamente desde los chunks sin pasar por clustering.",
      ],
      when: "Perfecto para preguntas panorámicas: resúmenes ejecutivos, visión general del documento, identificación de temas principales y conclusiones.",
      example: "¿De qué trata este documento? — Dame un resumen ejecutivo de 500 palabras. — ¿Cuáles son los puntos principales y conclusiones?",
    },
  },
];

export default function ModeInfoSection() {
  const [hoveredMode, setHoveredMode] = useState<string | null>(null);

  const active = modes.find((m) => m.id === hoveredMode);

  return (
    <div className="mt-16">
      <h3 className="mb-4 font-semibold text-gray-900 dark:text-gray-100">
        Modos de consulta
      </h3>
      <div
        className="relative"
        onMouseLeave={() => setHoveredMode(null)}
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {modes.map((mode) => {
            const Icon = mode.icon;
            const isDimmed = hoveredMode !== null && hoveredMode !== mode.id;
            return (
              <div
                key={mode.id}
                onMouseEnter={() => setHoveredMode(mode.id)}
                className={`rounded-xl border border-t-4 border-gray-200 bg-white p-5 shadow-sm transition-all duration-200 dark:border-gray-700 dark:bg-gray-800 ${mode.accentColor} ${
                  isDimmed ? "opacity-10" : ""
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {mode.name}
                  </span>
                  <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-medium ${mode.badgeColor}`}>
                    {mode.levels}
                  </span>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-gray-600 dark:text-gray-400">
                  {mode.description}
                </p>
                <p className="mt-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                  {mode.useCase}
                </p>
                <div className="mt-2 flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                  <ArrowRight className="h-3 w-3" />
                  <span className="italic">{mode.example}</span>
                </div>
              </div>
            );
          })}
        </div>

        {active && (
          <div className="absolute inset-0 z-10 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg transition-all duration-200 dark:border-gray-700 dark:bg-gray-800">
            <div className={`h-1.5 rounded-t-xl ${active.barColor}`} />
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <active.detailIcon className="h-6 w-6 text-gray-500 dark:text-gray-400" />
                  <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {active.name}
                  </span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${active.badgeColor}`}>
                    {active.levels}
                  </span>
                </div>
                <button
                  onClick={() => setHoveredMode(null)}
                  className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <p className="mt-4 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                {active.detail.what}
              </p>

              <div className="mt-4 space-y-2">
                {active.detail.how.map((step, i) => (
                  <div key={i} className="flex gap-2.5 text-sm text-gray-600 dark:text-gray-400">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-[10px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                      {i + 1}
                    </span>
                    <span dangerouslySetInnerHTML={{ __html: step }} />
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-lg bg-gray-50 p-4 dark:bg-gray-900/50">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  Cuándo usarlo
                </p>
                <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                  {active.detail.when}
                </p>
              </div>

              <div className="mt-3 flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
                <ArrowRight className="h-4 w-4" />
                <span className="italic">{active.detail.example}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
