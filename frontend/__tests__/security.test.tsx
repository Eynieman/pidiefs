import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { FileText } from "lucide-react";
import { MarkdownMessage } from "@/components/MarkdownMessage";
import { ErrorFallback } from "@/components/ErrorFallback";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { EmptyState } from "@/components/EmptyState";

describe("Security: MarkdownMessage XSS prevention", () => {
  it("does not render dangerous HTML from script tags", () => {
    const malicious = '<script>alert("xss")</script>';
    const { container } = render(<MarkdownMessage content={malicious} />);
    // rehype-sanitize debe eliminar la etiqueta script
    expect(container.innerHTML).not.toContain("<script>");
    expect(container.innerHTML).not.toContain("alert(");
  });

  it("does not render onclick handlers", () => {
    const malicious = '<a href="#" onclick="alert(1)">click me</a>';
    const { container } = render(<MarkdownMessage content={malicious} />);
    expect(container.innerHTML).not.toContain("onclick");
    expect(container.innerHTML).not.toContain("alert");
  });

  it("does not render iframe tags", () => {
    const malicious = '<iframe src="https://evil.com"></iframe>';
    const { container } = render(<MarkdownMessage content={malicious} />);
    expect(container.innerHTML).not.toContain("iframe");
    expect(container.innerHTML).not.toContain("evil.com");
  });

  it("does not render javascript: URLs", () => {
    const malicious = '<a href="javascript:alert(1)">link</a>';
    const { container } = render(<MarkdownMessage content={malicious} />);
    expect(container.innerHTML).not.toContain("javascript:");
  });

  it("sanitizes img tags with onerror handlers", () => {
    const malicious = '<img src=x onerror="alert(1)">';
    const { container } = render(<MarkdownMessage content={malicious} />);
    expect(container.innerHTML).not.toContain("onerror");
  });

  it("renders safe markdown normally", () => {
    const safe = "Hello **world**";
    const { container } = render(<MarkdownMessage content={safe} />);
    expect(container.innerHTML).toContain("Hello");
    expect(container.innerHTML).toContain("world");
  });
});

describe("Security: Component integrity", () => {
  it("ErrorFallback renders without errors", () => {
    const error = new Error("Test error");
    const reset = () => {};
    render(<ErrorFallback error={error} reset={reset} />);
    expect(screen.getByText(/algo salio mal/i)).toBeDefined();
  });

  it("LoadingSpinner renders without errors", () => {
    render(<LoadingSpinner message="Cargando..." />);
    expect(screen.getByText("Cargando...")).toBeDefined();
  });

  it("EmptyState renders without errors", () => {
    render(
      <EmptyState
        icon={FileText}
        title="Sin datos"
        description="No hay contenido"
      />
    );
    expect(screen.getByText("Sin datos")).toBeDefined();
  });
});
