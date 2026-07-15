"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileText, Loader2, X, CheckCircle2, AlertCircle } from "lucide-react";
import { StatusCard } from "@/components/StatusCard";

const MAX_FILE_SIZE = 50 * 1024 * 1024;

interface UploadResult {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
}

interface FileItem {
  file: File;
  status: "pending" | "uploading" | "processing" | "done" | "error";
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

  const handleUploadAll = useCallback(async () => {
    const toUpload = files.filter((f) => f.status === "pending");
    if (toUpload.length === 0) return;

    setUploading(true);

    for (const item of toUpload) {
      const idx = files.indexOf(item);
      setFiles((prev) =>
        prev.map((f, i) => (i === idx ? { ...f, status: "uploading" } : f)),
      );

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

        const data = await res.json();
        setFiles((prev) =>
          prev.map((f, i) =>
            i === idx ? { ...f, status: "done", result: data } : f,
          ),
        );
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error de conexion";
        setFiles((prev) =>
          prev.map((f, i) =>
            i === idx ? { ...f, status: "error", error: message } : f,
          ),
        );
      }
    }

    setUploading(false);
  }, [files]);

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const doneCount = files.filter((f) => f.status === "done").length;
  const hasFiles = files.length > 0;

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-gray-900">Subir PDF</h1>
      <p className="mt-1 text-sm text-gray-500">
        Se extraera el texto, se generaran embeddings y se indexara en la base vectorial
      </p>

      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`mt-8 rounded-xl border-2 border-dashed p-10 text-center transition ${
          isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-white hover:border-blue-400"
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
          <Upload className="mx-auto h-10 w-10 text-gray-400" />
          <p className="mt-3 text-sm text-gray-600">
            {isDragging ? (
              <span className="font-medium text-blue-600">Suelta los PDFs aqui</span>
            ) : (
              "Arrastra varios PDFs o click para seleccionar"
            )}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Solo archivos .pdf — Maximo 50 MB c/u
          </p>
        </label>
      </div>

      {hasFiles && (
        <div className="mt-4 space-y-2">
          {files.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2"
            >
              <FileText className="h-4 w-4 flex-shrink-0 text-gray-400" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-700">{item.file.name}</p>
                <p className="text-xs text-gray-400">{formatSize(item.file.size)}</p>
              </div>
              {item.status === "pending" && (
                <button
                  onClick={() => removeFile(i)}
                  className="rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              {item.status === "uploading" && (
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              )}
              {item.status === "done" && item.result && (
                <span className="text-xs text-green-600">
                  {item.result.chunks} chunks
                </span>
              )}
              {item.status === "done" && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              {item.status === "error" && (
                <span className="text-xs text-red-500" title={item.error}>
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
              Subiendo...
            </span>
          ) : doneCount > 0 ? (
            `Subir ${pendingCount} restante${pendingCount !== 1 ? "s" : ""}`
          ) : (
            `Subir ${files.length} archivo${files.length !== 1 ? "s" : ""}`
          )}
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
    </div>
  );
}
