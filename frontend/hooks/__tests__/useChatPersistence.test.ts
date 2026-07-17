import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useChatPersistence } from "../useChatPersistence";

describe("useChatPersistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("initializes with empty selectedDocIds", () => {
    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.selectedDocIds).toEqual([]);
  });

  it("initializes with stored selectedDocIds", () => {
    localStorage.setItem(
      "pidiefs-chat-selected-docs",
      JSON.stringify(["doc1", "doc2"])
    );
    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.selectedDocIds).toEqual(["doc1", "doc2"]);
  });

  it("saves messages to localStorage", () => {
    const { result } = renderHook(() => useChatPersistence());

    act(() => {
      result.current.setMessages([
        { role: "user", content: "hello" },
        { role: "assistant", content: "hi there" },
      ]);
    });

    const stored = localStorage.getItem("pidiefs-chat-doc-all");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed).toHaveLength(2);
    expect(parsed[0].content).toBe("hello");
  });

  it("loads messages from localStorage for specific doc", () => {
    localStorage.setItem(
      "pidiefs-chat-doc-doc123",
      JSON.stringify([{ role: "user", content: "doc specific" }])
    );
    localStorage.setItem(
      "pidiefs-chat-selected-docs",
      JSON.stringify(["doc123"])
    );

    const { result } = renderHook(() => useChatPersistence());

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("doc specific");
  });

  it("clearChat removes messages", () => {
    const { result } = renderHook(() => useChatPersistence());

    act(() => {
      result.current.setMessages([{ role: "user", content: "test" }]);
    });

    expect(result.current.messages).toHaveLength(1);

    act(() => {
      result.current.clearChat();
    });

    expect(result.current.messages).toEqual([]);
  });

  it("migrates legacy storage keys", async () => {
    localStorage.setItem(
      "pidiefs-chat-messages",
      JSON.stringify([{ role: "user", content: "legacy" }])
    );

    renderHook(() => useChatPersistence());

    await waitFor(() => {
      expect(localStorage.getItem("pidiefs-chat-messages")).toBeNull();
    });
  });

  it("limits stored messages to MAX_MESSAGES (50)", () => {
    const { result } = renderHook(() => useChatPersistence());

    const manyMessages = Array.from({ length: 60 }, (_, i) => ({
      role: "user" as const,
      content: `msg ${i}`,
    }));

    act(() => {
      result.current.setMessages(manyMessages);
    });

    const stored = localStorage.getItem("pidiefs-chat-doc-all");
    const parsed = JSON.parse(stored!);
    expect(parsed).toHaveLength(50);
    expect(parsed[0].content).toBe("msg 10");
  });

  it("switches messages when selectedDocIds changes", () => {
    localStorage.setItem(
      "pidiefs-chat-doc-docA",
      JSON.stringify([{ role: "user", content: "from A" }])
    );
    localStorage.setItem(
      "pidiefs-chat-doc-docB",
      JSON.stringify([{ role: "user", content: "from B" }])
    );

    const { result } = renderHook(() => useChatPersistence());

    act(() => {
      result.current.setSelectedDocIds(["docA"]);
    });
    expect(result.current.messages[0].content).toBe("from A");

    act(() => {
      result.current.setSelectedDocIds(["docB"]);
    });
    expect(result.current.messages[0].content).toBe("from B");
  });

  it("persists selectedDocIds to localStorage", () => {
    const { result } = renderHook(() => useChatPersistence());

    act(() => {
      result.current.setSelectedDocIds(["doc1", "doc2"]);
    });

    const stored = localStorage.getItem("pidiefs-chat-selected-docs");
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!)).toEqual(["doc1", "doc2"]);
  });

  it("loads all messages when selectedDocIds is empty", () => {
    localStorage.setItem(
      "pidiefs-chat-doc-all",
      JSON.stringify([{ role: "user", content: "all docs" }])
    );

    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("all docs");
  });

  it("loads single doc messages when one doc selected", () => {
    localStorage.setItem(
      "pidiefs-chat-doc-mydoc",
      JSON.stringify([{ role: "user", content: "my doc" }])
    );
    localStorage.setItem(
      "pidiefs-chat-selected-docs",
      JSON.stringify(["mydoc"])
    );

    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("my doc");
  });
});
