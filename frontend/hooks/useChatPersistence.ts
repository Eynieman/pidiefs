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
  localStorage.setItem(getDocKey(docId), JSON.stringify(toSave));
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
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    const activeDoc = getActiveDocId(prevDocIdsRef.current);
    localStorage.removeItem(getDocKey(activeDoc));
  }, []);

  return { messages, setMessages, selectedDocIds, setSelectedDocIds, clearChat };
}
