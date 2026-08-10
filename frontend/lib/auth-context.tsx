"use client";

/**
 * IMPORTANT: the FastAPI backend has no auth endpoints at all.
 * This is a real, but entirely client-side, account system backed by
 * localStorage. It exists so the redesigned dashboard has something to
 * guard behind. Every read/write to the account store goes through this
 * one file / the useAuth() hook, so swapping in real backend auth later
 * means changing this file only, not every page that calls useAuth().
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { PlanTier, StoredUser } from "./types";

const USERS_KEY = "studyforge:users";
const SESSION_KEY = "studyforge:session";

interface StoredUserRecord extends StoredUser {
  password: string;
}

interface AuthContextValue {
  user: StoredUser | null;
  isLoading: boolean;
  signup: (name: string, email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setPlan: (plan: PlanTier) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readUsers(): StoredUserRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(USERS_KEY);
    return raw ? (JSON.parse(raw) as StoredUserRecord[]) : [];
  } catch {
    return [];
  }
}

function writeUsers(users: StoredUserRecord[]) {
  window.localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function toPublicUser(record: StoredUserRecord): StoredUser {
  const { password: _password, ...publicUser } = record;
  void _password;
  return publicUser;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const sessionId = window.localStorage.getItem(SESSION_KEY);
      if (sessionId) {
        const match = readUsers().find((u) => u.id === sessionId);
        if (match) setUser(toPublicUser(match));
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const users = readUsers();
    if (users.some((u) => u.email === normalizedEmail)) {
      throw new Error("An account with that email already exists.");
    }
    const record: StoredUserRecord = {
      id: crypto.randomUUID(),
      name: name.trim(),
      email: normalizedEmail,
      password,
      plan: "scholar",
      createdAt: Date.now(),
    };
    writeUsers([...users, record]);
    window.localStorage.setItem(SESSION_KEY, record.id);
    setUser(toPublicUser(record));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const users = readUsers();
    const match = users.find(
      (u) => u.email === normalizedEmail && u.password === password
    );
    if (!match) {
      throw new Error("Invalid email or password.");
    }
    window.localStorage.setItem(SESSION_KEY, match.id);
    setUser(toPublicUser(match));
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(SESSION_KEY);
    setUser(null);
  }, []);

  const setPlan = useCallback(
    (plan: PlanTier) => {
      if (!user) return;
      const users = readUsers();
      const updated = users.map((u) => (u.id === user.id ? { ...u, plan } : u));
      writeUsers(updated);
      setUser({ ...user, plan });
    },
    [user]
  );

  const value = useMemo(
    () => ({ user, isLoading, signup, login, logout, setPlan }),
    [user, isLoading, signup, login, logout, setPlan]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
