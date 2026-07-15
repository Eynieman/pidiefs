import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusCard } from "@/components/StatusCard";

describe("StatusCard", () => {
  it("renders success card", () => {
    render(
      <StatusCard type="success" title="Exito">
        <p>Detalle</p>
      </StatusCard>
    );

    expect(screen.getByText("Exito")).toBeInTheDocument();
    expect(screen.getByText("Detalle")).toBeInTheDocument();
  });

  it("renders error card", () => {
    render(
      <StatusCard type="error" title="Error">
        <p>Mensaje de error</p>
      </StatusCard>
    );

    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("Mensaje de error")).toBeInTheDocument();
  });
});
