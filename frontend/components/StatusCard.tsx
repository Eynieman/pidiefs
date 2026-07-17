import { CheckCircle, AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

interface StatusCardProps {
  type: "success" | "error";
  title: string;
  children: ReactNode;
}

const styles = {
  success: {
    container: "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20",
    icon: "text-green-500 dark:text-green-400",
    title: "text-green-800 dark:text-green-200",
    content: "text-green-700 dark:text-green-300",
  },
  error: {
    container: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
    icon: "text-red-500 dark:text-red-400",
    title: "text-red-800 dark:text-red-200",
    content: "text-red-700 dark:text-red-300",
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
