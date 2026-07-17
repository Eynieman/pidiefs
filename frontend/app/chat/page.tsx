"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Trash2, Lightbulb, Square, AlertCircle, Copy, Check, Download } from "lucide-react";
import { SourceCitation } from "@/components/SourceCitation";
import { MarkdownMessage } from "@/components/MarkdownMessage";
import { useChatPersistence } from "@/hooks/useChatPersistence";

interface Document {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
}

const suggestions = [
  "¿De qué trata este documento?",
  "¿Cuáles son los puntos principales?",
  "Resume el contenido",
  "¿Qué conclusiones se pueden extraer?",
];

export default function ChatPage() {
  const {
    messages,
    setMessages,
    selectedDocIds,
    setSelectedDocIds,
    clearChat,
  } = useChatPersistence();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsError, setDocsError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const toggleDoc = (id: string) => {
    setSelectedDocIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((d) => d !== id);
      }
      return [...prev, id];
    });
  };

  const toggleAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map((d) => d.id));
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetch("/api/documents")
      .then((res) => res.json())
      .then((data) => setDocuments(data))
      .catch(() => setDocsError("No se pudo conectar con el backend"));
  }, []);

  const handleSend = useCallback(async (overrideQuestion?: string) => {
    const question = (overrideQuestion ?? input).trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    const body: { question: string; doc_ids?: string[] } = { question };
    if (selectedDocIds.length > 0) {
      body.doc_ids = selectedDocIds;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al consultar");
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No se pudo leer la respuesta");

      const decoder = new TextDecoder();
      let sources: { content: string; source: string; page: number; score: number }[] = [];
      let answer = "";
      let buffer = "";

      setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") break;

          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "sources") {
              sources = parsed.sources;
              setMessages((prev) => {
                const msgs = [...prev];
                const last = msgs[msgs.length - 1];
                if (last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, sources };
                }
                return msgs;
              });
            } else if (parsed.type === "token") {
              answer += parsed.content;
              const content = answer;
              setMessages((prev) => {
                const msgs = [...prev];
                const last = msgs[msgs.length - 1];
                if (last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content };
                }
                return msgs;
              });
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Generacion detenida por el usuario.", isError: true },
        ]);
      } else {
        const message = err instanceof Error ? err.message : "No se pudo conectar con el backend";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: message, isError: true },
        ]);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, loading, selectedDocIds]);

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleCopy = (content: string, idx: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleExport = () => {
    const lines: string[] = ["# Conversación Pidiefs\n"];
    for (const msg of messages) {
      if (msg.role === "user") {
        lines.push(`## Pregunta\n${msg.content}\n`);
      } else {
        lines.push(`## Respuesta\n${msg.content}\n`);
        if (msg.sources && msg.sources.length > 0) {
          lines.push("**Fuentes:**");
          for (const src of msg.sources) {
            lines.push(`- ${src.source} (pág. ${src.page}) — score: ${src.score}`);
          }
          lines.push("");
        }
      }
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-pidiefs-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4">
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Documentos ({selectedDocIds.length}/{documents.length})
          </span>
          {messages.length > 0 && (
            <div className="flex gap-1">
              <button
                onClick={handleExport}
                className="rounded-lg p-2 text-gray-400 transition hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
                title="Exportar conversación"
              >
                <Download className="h-4 w-4" />
              </button>
              <button
                onClick={clearChat}
                className="rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                title="Limpiar chat"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
        {docsError ? (
          <span className="text-sm text-red-500">{docsError}</span>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 transition hover:border-blue-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-blue-500">
              <input
                type="checkbox"
                checked={selectedDocIds.length === documents.length && documents.length > 0}
                onChange={toggleAll}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Todos
            </label>
            {documents.map((doc) => (
              <label
                key={doc.id}
                className="flex cursor-pointer items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 transition hover:border-blue-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-blue-500"
              >
                <input
                  type="checkbox"
                  checked={selectedDocIds.includes(doc.id)}
                  onChange={() => toggleDoc(doc.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                {doc.filename}
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <p className="text-lg font-medium text-gray-400 dark:text-gray-500">
              Haz una pregunta sobre tus documentos
            </p>
            <p className="mt-1 text-sm text-gray-300 dark:text-gray-600">
              {selectedDocIds.length === 0
                ? "Selecciona documentos para buscar"
                : selectedDocIds.length === documents.length
                  ? "Buscando en todos los documentos"
                  : `Buscando en ${selectedDocIds.length} documento(s)`}
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  disabled={loading}
                  className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-600 transition hover:border-blue-300 hover:text-blue-600 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-blue-500 dark:hover:text-blue-400"
                >
                  <Lightbulb className="h-3 w-3" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-6">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : msg.isError
                      ? "border border-red-200 bg-red-50 text-red-700 shadow-sm dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
                      : "border border-gray-200 bg-white text-gray-900 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
                }`}
              >
                {msg.role === "assistant" ? (
                  msg.isError ? (
                    <div className="flex items-start gap-2 text-sm">
                      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      <p>{msg.content}</p>
                    </div>
                  ) : (
                    <MarkdownMessage content={msg.content} />
                  )
                ) : (
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                )}
                {msg.sources && <SourceCitation sources={msg.sources} />}
                {msg.role === "assistant" && !msg.isError && msg.content && (
                  <button
                    onClick={() => handleCopy(msg.content, i)}
                    className="mt-2 flex items-center gap-1 text-xs text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {copiedIdx === i ? (
                      <><Check className="h-3 w-3" /> Copiado</>
                    ) : (
                      <><Copy className="h-3 w-3" /> Copiar</>
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm dark:border-gray-700 dark:bg-gray-800">
                <span className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Pensando...
                </span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white py-3 dark:border-gray-700 dark:bg-gray-900">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Escribe tu pregunta..."
            disabled={loading}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-blue-400"
          />
          {loading ? (
            <button
              onClick={handleStop}
              className="rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-red-700"
              title="Detener generacion"
            >
              <Square className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
