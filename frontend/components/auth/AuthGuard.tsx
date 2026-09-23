"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Spinner } from "@/components/ui/Primitives";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, profile, isLoading, isProfileLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isProfileLoading && !user) {
      router.replace("/login");
    }
    if (!isLoading && !isProfileLoading && user && !profile) {
      router.replace("/onboarding");
    }
  }, [isLoading, isProfileLoading, user, profile, router]);

  if (isLoading || isProfileLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-950">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  return <>{children}</>;
}