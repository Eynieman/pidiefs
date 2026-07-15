import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarkdownMessage } from "@/components/MarkdownMessage";

describe("MarkdownMessage", () => {
  it("renders plain text", () => {
    render(<MarkdownMessage content="Hello world" />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders markdown headings", () => {
    render(<MarkdownMessage content="## Title" />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Title");
  });

  it("renders bold text", () => {
    render(<MarkdownMessage content="**bold**" />);
    expect(screen.getByText("bold")).toHaveProperty("tagName", "STRONG");
  });

  it("renders lists", () => {
    render(<MarkdownMessage content={"- Item 1\n- Item 2"} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
  });
});
