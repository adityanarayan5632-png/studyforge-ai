"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { supabase } from "@/lib/supabase";
import type { PlanTier, StoredUser, StudentProfile } from "./types";

interface AuthContextValue {
  user: StoredUser | null;
  profile: StudentProfile | null;
  isLoading: boolean;
  isProfileLoading: boolean;
  signup: (name: string, email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  setPlan: (plan: PlanTier) => void;
  completeOnboarding: (profile: Omit<StudentProfile, "id" | "created_at" | "updated_at">) => Promise<void>;
  refreshProfile: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function mapSupabaseUser(user: { id: string; email?: string; user_metadata: Record<string, unknown> }): StoredUser {
  const email = user.email || "";
  return {
    id: user.id,
    name: (user.user_metadata?.full_name as string) || email.split("@")[0],
    email,
    plan: "scholar",
    createdAt: Date.now(),
  };
}

async function fetchProfileFromSupabase(sessionUserId: string): Promise<StudentProfile | null> {
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", sessionUserId)
    .single();

  if (error && error.code !== "PGRST116") {
    throw error;
  }
  return data || null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProfileLoading, setIsProfileLoading] = useState(false);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (mounted && session?.user) {
        setUser(mapSupabaseUser(session.user));
      }
      if (mounted) setIsLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (mounted && session?.user) {
        setUser(mapSupabaseUser(session.user));
      } else if (mounted && !session) {
        setUser(null);
        setProfile(null);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadProfile() {
      if (!user) {
        setProfile(null);
        return;
      }

      setIsProfileLoading(true);
      try {
        const data = await fetchProfileFromSupabase(user.id);
        if (mounted) setProfile(data);
      } catch (error) {
        console.error("Failed to fetch profile:", error);
        if (mounted) setProfile(null);
      } finally {
        if (mounted) setIsProfileLoading(false);
      }
    }

    loadProfile();

    return () => {
      mounted = false;
    };
  }, [user]);

  const signup = useCallback(async (name: string, email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email: email.trim().toLowerCase(),
      password,
      options: {
        data: {
          full_name: name.trim(),
        },
      },
    });
    if (error) throw new Error(error.message);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim().toLowerCase(),
      password,
    });
    if (error) throw new Error(error.message);
  }, []);

  const logout = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw new Error(error.message);
  }, []);

  const loginWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) throw new Error(error.message);
  }, []);

  const setPlan = useCallback(
    (plan: PlanTier) => {
      if (!user) return;
      setUser({ ...user, plan });
    },
    [user]
  );

  const completeOnboarding = useCallback(async (profileData: Omit<StudentProfile, "id" | "created_at" | "updated_at">) => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) throw new Error("Not authenticated");

    const { error } = await supabase
      .from("profiles")
      .insert({
        id: session.user.id,
        ...profileData,
      });

    if (error) throw new Error(error.message);

    const newProfile: StudentProfile = {
      id: session.user.id,
      ...profileData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setProfile(newProfile);
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!user) return;
    setIsProfileLoading(true);
    try {
      const data = await fetchProfileFromSupabase(user.id);
      setProfile(data);
    } catch (error) {
      console.error("Failed to refresh profile:", error);
      setProfile(null);
    } finally {
      setIsProfileLoading(false);
    }
  }, [user]);

  const getAccessToken = useCallback(async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }, []);

  const value = useMemo(
    () => ({
      user,
      profile,
      isLoading,
      isProfileLoading,
      signup,
      login,
      loginWithGoogle,
      logout,
      setPlan,
      completeOnboarding,
      refreshProfile,
      getAccessToken,
    }),
    [user, profile, isLoading, isProfileLoading, signup, login, loginWithGoogle, logout, setPlan, completeOnboarding, refreshProfile, getAccessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}