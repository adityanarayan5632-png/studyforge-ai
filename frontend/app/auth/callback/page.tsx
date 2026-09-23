"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Spinner } from "@/components/ui/Primitives";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    async function handleCallback() {
      const code = searchParams.get("code");
      const error = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      if (error) {
        console.error("OAuth error:", error, errorDescription);
        router.replace(`/login?error=${encodeURIComponent(errorDescription || error)}`);
        return;
      }

      if (code) {
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
        if (exchangeError) {
          console.error("Code exchange error:", exchangeError);
          router.replace(`/login?error=${encodeURIComponent(exchangeError.message)}`);
          return;
        }
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("*")
          .eq("id", session.user.id)
          .single();

        if (profile) {
          router.replace("/dashboard");
        } else {
          router.replace("/onboarding");
        }
      } else {
        router.replace("/login");
      }
    }

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950">
      <Spinner className="h-6 w-6" />
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-ink-950">
        <Spinner className="h-6 w-6" />
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}