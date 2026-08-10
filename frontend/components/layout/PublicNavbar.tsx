"use client";

import { Logo } from "./Logo";
import { LinkButton } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";

export function PublicNavbar() {
  const { user, isLoading } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700 bg-ink-950/85 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Logo />
        <div className="hidden items-center gap-8 md:flex">
          <a href="/#features" className="text-sm text-parchment-300 hover:text-parchment-100">
            Features
          </a>
          <a href="/#how-it-works" className="text-sm text-parchment-300 hover:text-parchment-100">
            How it works
          </a>
          <a href="/#pricing" className="text-sm text-parchment-300 hover:text-parchment-100">
            Pricing
          </a>
        </div>
        <div className="flex items-center gap-3">
          {!isLoading && user ? (
            <LinkButton href="/dashboard" size="sm">
              Go to dashboard
            </LinkButton>
          ) : (
            <>
              <LinkButton href="/login" variant="ghost" size="sm">
                Log in
              </LinkButton>
              <LinkButton href="/signup" size="sm">
                Start forging — free
              </LinkButton>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
