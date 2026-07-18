"use client";

import { useState, useCallback, useEffect, useRef } from "react";

const STORAGE_PREFIX = "pidiefs-chat-doc-";
const SELECTED_DOCS_KEY = "pidiefs-chat-selected-docs";
const PREV_STORAGE_KEY = "pidiefs-chat-messages";
const PREV_DOC_KEY = "pidiefs-chat-docid";
const MAX_MESSAGES = 50;

export interface Source {
  content: string;
  source: string;
  page: number;
  score: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isError?: boolean;
}

export interface Conversation {
  id: string;
  doc_ids: string[];
  title: string | null;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

function getDocKey(docId: string): string {
  return `${STORAGE_PREFIX}${docId}`;
}

function loadSelectedDocIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(SELECTED_DOCS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {}
  return [];
}

function saveSelectedDocIds(docIds: string[]) {
  localStorage.setItem(SELECTED_DOCS_KEY, JSON.stringify(docIds));
}

function loadMessagesForDoc(docId: string): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(getDocKey(docId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessagesForDoc(docId: string, msgs: Message[]) {
  const toSave = msgs.slice(-MAX_MESSAGES);
  try {
    localStorage.setItem(getDocKey(docId), JSON.stringify(toSave));
  } catch (e) {
    if (e instanceof DOMException && e.name === "QuotaExceededError") {
      const reduced = toSave.slice(-Math.floor(MAX_MESSAGES / 2));
      try {
        localStorage.setItem(getDocKey(docId), JSON.stringify(reduced));
      } catch {
        // Still failing, silently continue
      }
    }
  }
}

function migrateIfNeeded() {
  if (typeof window === "undefined") return;

  const legacy = localStorage.getItem(PREV_STORAGE_KEY);
  if (legacy) {
    localStorage.setItem(getDocKey("all"), legacy);
    localStorage.removeItem(PREV_STORAGE_KEY);
  }

  const prevDocId = localStorage.getItem(PREV_DOC_KEY);
  if (prevDocId) {
    localStorage.removeItem(PREV_DOC_KEY);
  }
}

function getActiveDocId(docIds: string[]): string {
  return docIds.length === 1 ? docIds[0] : "all";
}

export function useChatPersistence() {
  const [selectedDocIds, setSelectedDocIdsState] = useState<string[]>(loadSelectedDocIds);
  const [messages, setMessages] = useState<Message[]>(() =>
    loadMessagesForDoc(getActiveDocId(loadSelectedDocIds())),
  );
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const isInitialMount = useRef(true);
  const prevDocIdsRef = useRef(selectedDocIds);

  useEffect(() => {
    migrateIfNeeded();
  }, []);

  useEffect(() => {
    isInitialMount.current = false;
    const activeDoc = getActiveDocId(prevDocIdsRef.current);
    saveMessagesForDoc(activeDoc, messages);
  }, [messages]);

  useEffect(() => {
    if (JSON.stringify(prevDocIdsRef.current) === JSON.stringify(selectedDocIds)) return;
    const prevActive = getActiveDocId(prevDocIdsRef.current);
    saveMessagesForDoc(prevActive, messages);
    const newActive = getActiveDocId(selectedDocIds);
    setMessages(loadMessagesForDoc(newActive));
    prevDocIdsRef.current = selectedDocIds;
    saveSelectedDocIds(selectedDocIds);
  }, [selectedDocIds]);

  const setSelectedDocIds = useCallback((docIds: string[] | ((prev: string[]) => string[])) => {
    setSelectedDocIdsState((prev) => {
      const next = typeof docIds === "function" ? docIds(prev) : docIds;
      return next;
    });
    setActiveConversationId(null);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setActiveConversationId(null);
    const activeDoc = getActiveDocId(prevDocIdsRef.current);
    localStorage.removeItem(getDocKey(activeDoc));
  }, []);

  const saveConversation = useCallback(async (title?: string): Promise<Conversation | null> => {
    try {
      const response = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_ids: selectedDocIds,
          title: title || messages[0]?.content?.slice(0, 50) || "Sin título",
        }),
      });
      if (!response.ok) return null;
      const conv = await response.json();

      for (const msg of messages) {
        await fetch(`/api/conversations/${conv.id}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: msg.role,
            content: msg.content,
            sources: msg.sources || null,
          }),
        });
      }

      setActiveConversationId(conv.id);
      return conv;
    } catch {
      return null;
    }
  }, [selectedDocIds, messages]);

  const loadConversations = useCallback(async (): Promise<Conversation[]> => {
    try {
      const response = await fetch("/api/conversations");
      if (!response.ok) return [];
      const convs = await response.json();
      setConversations(convs);
      return convs;
    } catch {
      return [];
    }
  }, []);

  const loadConversation = useCallback(async (conversationId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`);
      if (!response.ok) return false;
      const conv = await response.json();
      setSelectedDocIdsState(conv.doc_ids);
      setMessages(conv.messages || []);
      setActiveConversationId(conversationId);
      return true;
    } catch {
      return false;
    }
  }, []);

  const deleteConversation = useCallback(async (conversationId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: "DELETE",
      });
      if (!response.ok) return false;
      if (activeConversationId === conversationId) {
        setActiveConversationId(null);
      }
      return true;
    } catch {
      return false;
    }
  }, [activeConversationId]);

  return {
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
  };
}
