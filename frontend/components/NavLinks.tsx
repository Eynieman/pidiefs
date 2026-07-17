"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Inicio" },
  { href: "/upload", label: "Subir PDF" },
  { href: "/documents", label: "Documentos" },
  { href: "/chat", label: "Consultar" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-4 text-sm">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`transition-colors ${
            pathname === link.href
              ? "font-medium text-blue-600 dark:text-blue-400"
              : "text-gray-600 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
