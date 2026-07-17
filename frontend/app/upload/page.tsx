"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileText, Loader2, X, CheckCircle2, AlertCircle, AlertTriangle, RotateCcw, Trash } from "lucide-react";
import { StatusCard } from "@/components/StatusCard";

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const CONCURRENT_UPLOADS = 3;

interface UploadResult {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  duplicate_of: string | null;
}

interface FileItem {
  file: File;
  status: "pending" | "uploading" | "processing" | "done" | "error" | "duplicate";
  result?: UploadResult;
  error?: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(f: File): string | null {
  if (!f.name.toLowerCase().endsWith(".pdf")) return "Solo se permiten archivos PDF";
  if (f.size > MAX_FILE_SIZE) return `Excede 50 MB (${formatSize(f.size)})`;
  return null;
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const items: FileItem[] = [];
    for (const f of Array.from(newFiles)) {
      const err = validateFile(f);
      items.push({
        file: f,
        status: err ? "error" : "pending",
        error: err ?? undefined,
      });
    }
    setFiles((prev) => [...prev, ...items]);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const retryFile = (index: number) => {
    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, status: "pending", error: undefined } : f))
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
  };

  const uploadSingle = useCallback(async (item: FileItem, idx: number) => {
    const formData = new FormData();
    formData.append("file", item.file);

    try {
      const res = await fetch("/api/documents", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al subir");
      }

      const data: UploadResult = await res.json();

      setFiles((prev) =>
        prev.map((f, i) =>
          i === idx
            ? { ...f, status: data.duplicate_of ? "duplicate" : "done", result: data }
            : f
        ),
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error de conexion";
      setFiles((prev) =>
        prev.map((f, i) =>
          i === idx ? { ...f, status: "error", error: message } : f
        ),
      );
    }
  }, []);

  const handleUploadAll = useCallback(async () => {
    const toUpload = files
      .map((f, i) => ({ item: f, idx: i }))
      .filter(({ item }) => item.status === "pending");
    if (toUpload.length === 0) return;

    setUploading(true);

    setFiles((prev) =>
      prev.map((f) => (f.status === "pending" ? { ...f, status: "uploading" } : f))
    );

    for (let i = 0; i < toUpload.length; i += CONCURRENT_UPLOADS) {
      const batch = toUpload.slice(i, i + CONCURRENT_UPLOADS);
      await Promise.allSettled(
        batch.map(({ item, idx }) => uploadSingle({ ...item, status: "uploading" }, idx))
      );
    }

    setUploading(false);
  }, [files, uploadSingle]);

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const uploadingCount = files.filter((f) => f.status === "uploading").length;
  const doneCount = files.filter((f) => f.status === "done").length;
  const duplicateCount = files.filter((f) => f.status === "duplicate").length;
  const hasFiles = files.length > 0;

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Subir PDF</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Se extraera el texto, se generaran embeddings y se indexara en la base vectorial
      </p>

      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`mt-8 rounded-xl border-2 border-dashed p-10 text-center transition ${
          isDragging
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 bg-white hover:border-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-blue-500"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileChange}
          className="hidden"
          id="file-input"
        />
        <label htmlFor="file-input" className="cursor-pointer">
          <Upload className="mx-auto h-10 w-10 text-gray-400 dark:text-gray-500" />
          <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
            {isDragging ? (
              <span className="font-medium text-blue-600 dark:text-blue-400">Suelta los PDFs aqui</span>
            ) : (
              "Arrastra varios PDFs o click para seleccionar"
            )}
          </p>
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
            Solo archivos .pdf — Maximo 50 MB c/u
          </p>
        </label>
      </div>

      {hasFiles && (
        <div className="mt-4 space-y-2">
          {files.map((item, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${
                item.status === "duplicate"
                  ? "border-yellow-200 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/20"
                  : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
              }`}
            >
              <FileText className="h-4 w-4 flex-shrink-0 text-gray-400 dark:text-gray-500" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-700 dark:text-gray-200">{item.file.name}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{formatSize(item.file.size)}</p>
              </div>
              {item.status === "pending" && (
                <button
                  onClick={() => removeFile(i)}
                  className="rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              {item.status === "uploading" && (
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              )}
              {item.status === "done" && item.result && (
                <span className="text-xs text-green-600 dark:text-green-400">
                  {item.result.chunks} chunks
                </span>
              )}
              {item.status === "done" && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              {item.status === "duplicate" && (
                <span className="text-xs text-yellow-600 dark:text-yellow-400">
                  Duplicado
                </span>
              )}
              {item.status === "duplicate" && (
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
              )}
              {item.status === "error" && (
                <button
                  onClick={() => retryFile(i)}
                  className="rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-blue-600 dark:hover:bg-gray-700 dark:hover:text-blue-400"
                  title="Reintentar"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
              )}
              {item.status === "error" && (
                <span className="text-xs text-red-500 dark:text-red-400" title={item.error}>
                  Error
                </span>
              )}
              {item.status === "error" && (
                <AlertCircle className="h-4 w-4 text-red-500" />
              )}
            </div>
          ))}
        </div>
      )}

      {hasFiles && (
        <button
          onClick={handleUploadAll}
          disabled={uploading || pendingCount === 0}
          className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Subiendo {uploadingCount}...
            </span>
          ) : doneCount > 0 ? (
            `Subir ${pendingCount} restante${pendingCount !== 1 ? "s" : ""}`
          ) : (
            `Subir ${files.length} archivo${files.length !== 1 ? "s" : ""}`
          )}
        </button>
      )}

      {hasFiles && (doneCount > 0 || duplicateCount > 0) && (
        <button
          onClick={() => setFiles([])}
          className="mt-2 flex items-center gap-1.5 text-sm text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <Trash className="h-3.5 w-3.5" />
          Limpiar lista
        </button>
      )}

      {!hasFiles && (
        <StatusCard type="success" title="Ningun archivo seleccionado">
          <p>Selecciona uno o mas PDFs para comenzar</p>
        </StatusCard>
      )}

      {doneCount > 0 && (
        <StatusCard type="success" title={`${doneCount} archivo${doneCount !== 1 ? "s" : ""} indexado${doneCount !== 1 ? "s" : ""}`}>
          {files
            .filter((f) => f.status === "done" && f.result)
            .map((f) => (
              <p key={f.result!.id}>
                {f.result!.filename} — {f.result!.pages}p, {f.result!.chunks}c
              </p>
            ))}
        </StatusCard>
      )}

      {duplicateCount > 0 && (
        <div className="mt-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-700 dark:bg-yellow-900/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-500 dark:text-yellow-400" />
            <div>
              <p className="font-medium text-yellow-800 dark:text-yellow-200">
                {duplicateCount} duplicado{duplicateCount !== 1 ? "s" : ""} detectado{duplicateCount !== 1 ? "s" : ""}
              </p>
              <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                Estos archivos ya existen en la base de datos pero fueron indexados de todas formas.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
