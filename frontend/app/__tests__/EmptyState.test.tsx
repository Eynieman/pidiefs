import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/EmptyState";
import { FolderOpen } from "lucide-react";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState
        icon={FolderOpen}
        title="No hay documentos"
        description="Sube un PDF"
      />
    );

    expect(screen.getByText("No hay documentos")).toBeInTheDocument();
    expect(screen.getByText("Sube un PDF")).toBeInTheDocument();
  });
});
