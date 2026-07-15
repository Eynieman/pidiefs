"use client";

import { useState, useCallback, useEffect, useRef } from "react";

const STORAGE_PREFIX = "pidiefs-chat-doc-";
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
}

function getDocKey(docId: string): string {
  return `${STORAGE_PREFIX}${docId}`;
}

function loadDocId(): string {
  if (typeof window === "undefined") return "all";
  const stored = localStorage.getItem(PREV_DOC_KEY);
  if (stored) {
    localStorage.removeItem(PREV_DOC_KEY);
    return stored;
  }
  return "all";
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
  localStorage.setItem(getDocKey(docId), JSON.stringify(toSave));
}

function migrateIfNeeded() {
  if (typeof window === "undefined") return;
  const legacy = localStorage.getItem(PREV_STORAGE_KEY);
  if (legacy) {
    localStorage.setItem(getDocKey("all"), legacy);
    localStorage.removeItem(PREV_STORAGE_KEY);
  }
}

export function useChatPersistence() {
  const [selectedDocId, setSelectedDocIdState] = useState<string>(loadDocId);
  const [messages, setMessages] = useState<Message[]>(() =>
    loadMessagesForDoc(selectedDocId),
  );
  const isInitialMount = useRef(true);
  const prevDocIdRef = useRef(selectedDocId);

  useEffect(() => {
    migrateIfNeeded();
  }, []);

  useEffect(() => {
    isInitialMount.current = false;
    saveMessagesForDoc(prevDocIdRef.current, messages);
  }, [messages]);

  useEffect(() => {
    if (prevDocIdRef.current === selectedDocId) return;
    saveMessagesForDoc(prevDocIdRef.current, messages);
    setMessages(loadMessagesForDoc(selectedDocId));
    prevDocIdRef.current = selectedDocId;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDocId]);

  const setSelectedDocId = useCallback((docId: string) => {
    setSelectedDocIdState(docId);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(getDocKey(prevDocIdRef.current));
  }, []);

  return { messages, setMessages, selectedDocId, setSelectedDocId, clearChat };
}
