"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Trash2, Lightbulb, Square, AlertCircle, Copy, Check, Save, FolderOpen } from "lucide-react";
import { SourceCitation } from "@/components/SourceCitation";
import { MarkdownMessage } from "@/components/MarkdownMessage";
import { ChatExportMenu } from "@/components/ChatExportMenu";
import { useChatPersistence, Conversation } from "@/hooks/useChatPersistence";

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
    conversations,
    activeConversationId,
    saveConversation,
    loadConversations,
    loadConversation,
    deleteConversation,
  } = useChatPersistence();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsError, setDocsError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [showConversations, setShowConversations] = useState(false);
  const [saving, setSaving] = useState(false);

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
            } else if (parsed.type === "error") {
              setMessages((prev) => {
                const msgs = [...prev];
                const last = msgs[msgs.length - 1];
                if (last.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content: parsed.content, isError: true };
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

  const handleSave = async () => {
    if (messages.length === 0) return;
    setSaving(true);
    await saveConversation();
    setSaving(false);
  };

  const handleLoadConversations = async () => {
    if (showConversations) {
      setShowConversations(false);
    } else {
      await loadConversations();
      setShowConversations(true);
    }
  };

  const handleLoadConversation = async (conv: Conversation) => {
    await loadConversation(conv.id);
    setShowConversations(false);
  };

  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    await deleteConversation(convId);
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
                onClick={handleSave}
                disabled={saving || messages.length === 0}
                className="rounded-lg p-2 text-gray-400 transition hover:bg-green-50 hover:text-green-600 dark:hover:bg-green-900/20 dark:hover:text-green-400 disabled:opacity-50"
                title="Guardar conversación"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              </button>
              <button
                onClick={handleLoadConversations}
                className="rounded-lg p-2 text-gray-400 transition hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
                title="Cargar conversación"
              >
                <FolderOpen className="h-4 w-4" />
              </button>
              <ChatExportMenu messages={messages} />
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

      {showConversations && (
        <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Conversaciones guardadas</span>
            <button onClick={() => setShowConversations(false)} className="text-xs text-gray-400 hover:text-gray-600">Cerrar</button>
          </div>
          {conversations.length === 0 ? (
            <p className="text-xs text-gray-400">No hay conversaciones guardadas</p>
          ) : (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => handleLoadConversation(conv)}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs cursor-pointer transition ${
                    activeConversationId === conv.id
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                      : "hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  <div className="truncate flex-1">
                    <span className="font-medium">{conv.title || "Sin título"}</span>
                    <span className="ml-2 text-gray-400">{conv.doc_ids.length} doc(s)</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    className="ml-2 p-1 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
