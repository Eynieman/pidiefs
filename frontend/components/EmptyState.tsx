import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="mt-12 flex flex-col items-center justify-center text-center">
      <Icon className="h-12 w-12 text-gray-300 dark:text-gray-500" />
      <p className="mt-4 text-lg font-medium text-gray-400 dark:text-gray-500">{title}</p>
      <p className="mt-1 text-sm text-gray-300 dark:text-gray-500">{description}</p>
    </div>
  );
}
