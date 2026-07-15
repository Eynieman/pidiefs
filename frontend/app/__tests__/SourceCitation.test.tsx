import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceCitation } from "@/components/SourceCitation";

describe("SourceCitation", () => {
  it("renders nothing when sources are empty", () => {
    const { container } = render(<SourceCitation sources={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders source citations", () => {
    const sources = [
      { content: "text", source: "doc1.pdf", page: 1, score: 0.85 },
      { content: "text2", source: "doc2.pdf", page: 3, score: 0.72 },
    ];

    render(<SourceCitation sources={sources} />);

    expect(screen.getByText("Fuentes:")).toBeInTheDocument();
    expect(screen.getByText(/doc1\.pdf p\.1/)).toBeInTheDocument();
    expect(screen.getByText(/doc2\.pdf p\.3/)).toBeInTheDocument();
  });
});
