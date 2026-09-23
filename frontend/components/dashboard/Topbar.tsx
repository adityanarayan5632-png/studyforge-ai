"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/tutor", label: "AI Tutor" },
  { href: "/dashboard/notes", label: "Notes" },
  { href: "/dashboard/study", label: "Quiz & Flashcards" },
  { href: "/dashboard/settings", label: "Settings" },
];

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/tutor": "AI Tutor",
  "/dashboard/notes": "Notes",
  "/dashboard/study": "Quiz & Flashcards",
  "/dashboard/settings": "Settings",
};

export function Topbar() {
  const { user, profile, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  const title = PAGE_TITLES[pathname] ?? "Dashboard";

  const displayName = profile?.display_name || user?.name;

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-30 border-b border-ink-700 bg-ink-950/90 backdrop-blur-md">
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <button
            className="rounded-md p-2 text-parchment-300 hover:bg-ink-800 md:hidden"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle navigation"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M2 5h16M2 10h16M2 15h16" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
          <h1 className="font-display text-xl text-parchment-100">{title}</h1>
        </div>
        <div className="flex items-center gap-3">
          {user && <Badge tone="ember">{user.plan === "forgemaster" ? "Forgemaster" : "Scholar"}</Badge>}
          <span className="hidden text-sm text-parchment-500 sm:inline">{displayName}</span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Log out
          </Button>
        </div>
      </div>
      {mobileOpen && (
        <nav className="flex flex-col gap-1 border-t border-ink-700 px-4 py-3 md:hidden">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`rounded-md px-3 py-2 text-sm ${
                pathname === item.href
                  ? "bg-ember-500/12 text-ember-400"
                  : "text-parchment-300 hover:bg-ink-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
