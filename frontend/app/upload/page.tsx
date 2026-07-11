"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface UploadResult {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/documents", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al subir el archivo");
      }

      const data = await res.json();
      setResult(data);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err: any) {
      setError(err.message || "Error de conexion con el backend");
    } finally {
      setUploading(false);
    }
  }, [file]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-gray-900">Subir PDF</h1>
      <p className="mt-1 text-sm text-gray-500">
        Se extraera el texto, se generaran embeddings y se indexara en la base vectorial
      </p>

      <div className="mt-8 rounded-xl border-2 border-dashed border-gray-300 bg-white p-10 text-center transition hover:border-blue-400">
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
          id="file-input"
        />
        <label htmlFor="file-input" className="cursor-pointer">
          <Upload className="mx-auto h-10 w-10 text-gray-400" />
          <p className="mt-3 text-sm text-gray-600">
            {file ? (
              <span className="flex items-center justify-center gap-2">
                <FileText className="h-4 w-4" />
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </span>
            ) : (
              "Click para seleccionar un PDF"
            )}
          </p>
          <p className="mt-1 text-xs text-gray-400">Solo archivos .pdf</p>
        </label>
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Procesando...
          </span>
        ) : (
          "Subir e Indexar"
        )}
      </button>

      {result && (
        <div className="mt-6 rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
            <div>
              <p className="font-medium text-green-800">
                Documento indexado correctamente
              </p>
              <div className="mt-2 text-sm text-green-700">
                <p>Archivo: {result.filename}</p>
                <p>Paginas: {result.pages}</p>
                <p>Chunks generados: {result.chunks}</p>
                <p className="mt-1 text-xs text-green-600">ID: {result.id}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Error</p>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
