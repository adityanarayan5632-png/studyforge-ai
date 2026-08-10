"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/layout/Logo";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", exact: true },
  { href: "/dashboard/tutor", label: "AI Tutor" },
  { href: "/dashboard/notes", label: "Notes" },
  { href: "/dashboard/study", label: "Quiz & Flashcards" },
  { href: "/dashboard/settings", label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-ink-700 bg-ink-900 px-4 py-6 md:flex">
      <div className="px-2">
        <Logo href="/dashboard" />
      </div>
      <nav className="mt-10 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-ember-500/12 text-ember-400 border-l-2 border-ember-500 pl-[10px]"
                  : "text-parchment-500 hover:bg-ink-800 hover:text-parchment-100"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
