"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, FileText } from "lucide-react";

interface Document {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
}

interface Source {
  content: string;
  source: string;
  page: number;
  score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("all");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetch("http://localhost:8000/api/documents")
      .then((res) => res.json())
      .then((data) => setDocuments(data))
      .catch(() => {});
  }, []);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    const body: { question: string; doc_id?: string } = { question };
    if (selectedDocId !== "all") {
      body.doc_id = selectedDocId;
    }

    try {
      const res = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al consultar");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sources: data.sources },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err.message || "No se pudo conectar con el backend"}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const selectedDoc = documents.find((d) => d.id === selectedDocId);

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4">
      <div className="flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3">
        <label htmlFor="doc-select" className="text-sm font-medium text-gray-700">
          Documento:
        </label>
        <select
          id="doc-select"
          value={selectedDocId}
          onChange={(e) => setSelectedDocId(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">Todos los documentos</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.filename} ({doc.pages}p, {doc.chunks}c)
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <p className="text-lg font-medium text-gray-400">
              Haz una pregunta sobre tus documentos
            </p>
            <p className="mt-1 text-sm text-gray-300">
              {selectedDoc
                ? `Buscando en: ${selectedDoc.filename}`
                : "Buscando en todos los documentos"}
            </p>
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
                    : "bg-white text-gray-900 shadow-sm border border-gray-200"
                }`}
              >
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 border-t border-gray-100 pt-3">
                    <p className="text-xs font-medium text-gray-400 mb-2">
                      Fuentes:
                    </p>
                    <div className="space-y-1.5">
                      {msg.sources.map((src, j) => (
                        <div
                          key={j}
                          className="flex items-start gap-1.5 text-xs text-gray-500"
                        >
                          <FileText className="mt-0.5 h-3 w-3 flex-shrink-0" />
                          <span>
                            {src.source} p.{src.page}{" "}
                            <span className="text-gray-300">
                              ({(src.score * 100).toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-white px-4 py-3 shadow-sm border border-gray-200">
                <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Escribe tu pregunta..."
            disabled={loading}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
