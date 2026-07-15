import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorFallback } from "@/components/ErrorFallback";

describe("ErrorFallback", () => {
  it("renders error message", () => {
    const error = new Error("Test error message");
    const reset = vi.fn();

    render(<ErrorFallback error={error} reset={reset} />);

    expect(screen.getByText("Algo salio mal")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });

  it("renders retry button that calls reset", async () => {
    const error = new Error("Test error");
    const reset = vi.fn();

    render(<ErrorFallback error={error} reset={reset} />);

    const button = screen.getByRole("button", { name: /reintentar/i });
    expect(button).toBeInTheDocument();

    button.click();
    expect(reset).toHaveBeenCalledOnce();
  });
});
