import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingSpinner } from "@/components/LoadingSpinner";

describe("LoadingSpinner", () => {
  it("renders spinner without message", () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders spinner with message", () => {
    render(<LoadingSpinner message="Cargando..." />);
    expect(screen.getByText("Cargando...")).toBeInTheDocument();
  });
});
