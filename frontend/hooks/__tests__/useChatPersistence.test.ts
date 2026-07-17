import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useChatPersistence } from "../useChatPersistence";

describe("useChatPersistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("initializes with empty messages", () => {
    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.messages).toEqual([]);
  });

  it("initializes with 'all' as default docId", () => {
    const { result } = renderHook(() => useChatPersistence());
    expect(result.current.selectedDocId).toBe("all");
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

    const { result } = renderHook(() => useChatPersistence());

    act(() => {
      result.current.setSelectedDocId("doc123");
    });

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

  it("switches messages when doc changes", () => {
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
      result.current.setSelectedDocId("docA");
    });
    expect(result.current.messages[0].content).toBe("from A");

    act(() => {
      result.current.setSelectedDocId("docB");
    });
    expect(result.current.messages[0].content).toBe("from B");
  });
});
