import { CheckCircle, AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

interface StatusCardProps {
  type: "success" | "error";
  title: string;
  children: ReactNode;
}

const styles = {
  success: {
    container: "border-green-200 bg-green-50",
    icon: "text-green-500",
    title: "text-green-800",
    content: "text-green-700",
  },
  error: {
    container: "border-red-200 bg-red-50",
    icon: "text-red-500",
    title: "text-red-800",
    content: "text-red-700",
  },
};

export function StatusCard({ type, title, children }: StatusCardProps) {
  const s = styles[type];
  const Icon = type === "success" ? CheckCircle : AlertCircle;

  return (
    <div className={`mt-6 rounded-lg border p-4 ${s.container}`}>
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 flex-shrink-0 ${s.icon}`} />
        <div>
          <p className={`font-medium ${s.title}`}>{title}</p>
          <div className={`mt-2 text-sm ${s.content}`}>{children}</div>
        </div>
      </div>
    </div>
  );
}
