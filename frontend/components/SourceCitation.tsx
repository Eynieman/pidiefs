import { FileText } from "lucide-react";

interface Source {
  content: string;
  source: string;
  page: number;
  score: number;
}

interface SourceCitationProps {
  sources: Source[];
}

export function SourceCitation({ sources }: SourceCitationProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <p className="mb-2 text-xs font-medium text-gray-400">Fuentes:</p>
      <div className="space-y-1.5">
        {sources.map((src, j) => (
          <div
            key={j}
            className="flex items-start gap-1.5 text-xs text-gray-500"
          >
            <FileText className="mt-0.5 h-3 w-3 flex-shrink-0" />
            <span>
              {src.source} p.{src.page}{" "}
              <span className="text-gray-300">
                ({(src.score * 100).toFixed(0)}%)
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
