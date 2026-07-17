"use client";

import { useState } from "react";
import { Download, FileText, FileDown, ChevronDown } from "lucide-react";
import { Message } from "@/hooks/useChatPersistence";

interface ChatExportMenuProps {
  messages: Message[];
}

export function ChatExportMenu({ messages }: ChatExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const exportMarkdown = () => {
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
    setIsOpen(false);
  };

  const exportPDF = async () => {
    try {
      const { jsPDF } = await import("jspdf");
      const doc = new jsPDF();

      doc.setFontSize(18);
      doc.text("Conversacion Pidiefs", 20, 20);
      doc.setFontSize(10);
      doc.text(new Date().toLocaleDateString("es-AR"), 20, 28);

      let y = 40;
      const lineHeight = 7;
      const maxWidth = 170;

      for (const msg of messages) {
        if (y > 260) {
          doc.addPage();
          y = 20;
        }

        const role = msg.role === "user" ? "Pregunta" : "Respuesta";
        doc.setFontSize(11);
        doc.setFont("helvetica", "bold");
        doc.text(`${role}:`, 20, y);
        y += lineHeight;

        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        const lines = doc.splitTextToSize(msg.content, maxWidth);
        for (const line of lines) {
          if (y > 270) {
            doc.addPage();
            y = 20;
          }
          doc.text(line, 20, y);
          y += 5;
        }
        y += 3;

        if (msg.sources && msg.sources.length > 0) {
          doc.setFontSize(8);
          doc.setFont("helvetica", "italic");
          for (const src of msg.sources) {
            if (y > 270) {
              doc.addPage();
              y = 20;
            }
            doc.text(`Fuente: ${src.source} (pag. ${src.page})`, 20, y);
            y += 4;
          }
        }
        y += 5;
      }

      doc.save(`chat-pidiefs-${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (err) {
      console.error("Error generating PDF:", err);
    }
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 rounded-lg p-2 text-gray-400 transition hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
        title="Exportar conversación"
      >
        <Download className="h-4 w-4" />
        <ChevronDown className="h-3 w-3" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">
            <button
              onClick={exportMarkdown}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <FileText className="h-4 w-4" />
              Exportar Markdown
            </button>
            <button
              onClick={exportPDF}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <FileDown className="h-4 w-4" />
              Exportar PDF
            </button>
          </div>
        </>
      )}
    </div>
  );
}
