"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { listSources, listCurriculumSources } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SourceDocument, CurriculumSource } from "@/lib/types";

const SOURCES_KEY = "studyforge:sources";
const ACTIVE_SOURCE_KEY = "studyforge:activeSourceId";
const NOTES_KEY = "studyforge:notes";
const QUIZ_KEY = "studyforge:quiz";
const CURRICULUM_KEY = "studyforge:curriculum";

function getStoredSources(): SourceDocument[] {
  if (typeof window === "undefined") return [];
  const stored = window.sessionStorage.getItem(SOURCES_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored);
  } catch {
    window.sessionStorage.removeItem(SOURCES_KEY);
    return [];
  }
}

function getStoredActiveSourceId(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACTIVE_SOURCE_KEY);
}

function getStoredNotes(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(NOTES_KEY);
}

function getStoredQuiz(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(QUIZ_KEY);
}

function getStoredCurriculum(): CurriculumSource | null {
  if (typeof window === "undefined") return null;
  const stored = window.sessionStorage.getItem(CURRICULUM_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored);
  } catch {
    window.sessionStorage.removeItem(CURRICULUM_KEY);
    return null;
  }
}

interface StudyContextValue {
  sources: SourceDocument[];
  activeSourceId: string | null;
  notes: string | null;
  quiz: string | null;
  hasSources: boolean;
  addSource: (source: SourceDocument) => void;
  setActiveSource: (sourceId: string | null) => void;
  removeSource: (sourceId: string) => void;
  loadSources: () => Promise<void>;
  setNotes: (notes: string) => void;
  setQuiz: (quiz: string) => void;
  clearAll: () => void;
  // Curriculum state
  curriculumSources: CurriculumSource[];
  curriculumActive: boolean;
  curriculumGrade: number | null;
  curriculumSource: CurriculumSource | null;
  curriculumChapterNumber: number | null;
  setCurriculumMode: (active: boolean, grade?: number, source?: CurriculumSource | null, chapterNumber?: number | null) => void;
  loadCurriculumSources: () => Promise<void>;
}

const StudyContext = createContext<StudyContextValue | undefined>(undefined);

export function StudyProvider({ children }: { children: React.ReactNode }) {
  const [sources, setSources] = useState<SourceDocument[]>(() => getStoredSources());
  const [activeSourceId, setActiveSourceId] = useState<string | null>(() => getStoredActiveSourceId());
  const [notes, setNotesState] = useState<string | null>(() => getStoredNotes());
  const [quiz, setQuizState] = useState<string | null>(() => getStoredQuiz());
  // Curriculum state
  const [curriculumSources, setCurriculumSources] = useState<CurriculumSource[]>([]);
  const [curriculumActive, setCurriculumActive] = useState(false);
  const [curriculumGrade, setCurriculumGrade] = useState<number | null>(null);
  const [curriculumSource, setCurriculumSource] = useState<CurriculumSource | null>(null);
  const [curriculumChapterNumber, setCurriculumChapterNumber] = useState<number | null>(null);
  const { getAccessToken, user, isLoading, profile } = useAuth();

  // Fetch user sources from backend and reconcile on mount
  useEffect(() => {
    let mounted = true;
    async function fetchSources() {
      // Wait for auth loading to complete
      if (isLoading) {
        return;
      }
      
      // Only fetch sources if user is authenticated
      if (!user) {
        if (mounted) {
          setSources([]);
          setActiveSourceId(null);
        }
        return;
      }

      try {
        const accessToken = await getAccessToken();
        const backendSources = await listSources(accessToken);
        if (mounted) {
          setSources(backendSources);
          // Reset activeSourceId if it no longer exists
          if (activeSourceId && !backendSources.some((s) => s.id === activeSourceId)) {
            setActiveSourceId(null);
            if (typeof window !== "undefined") {
              window.sessionStorage.removeItem(ACTIVE_SOURCE_KEY);
            }
          }
        }
      } catch (error) {
        console.error("Failed to load sources:", error);
      }
    }
    fetchSources();
    return () => { mounted = false; };
  }, [isLoading, user, activeSourceId, getAccessToken]);

  // Persist sources to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(SOURCES_KEY, JSON.stringify(sources));
    }
  }, [sources]);

  // Persist activeSourceId to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (activeSourceId) {
        window.sessionStorage.setItem(ACTIVE_SOURCE_KEY, activeSourceId);
      } else {
        window.sessionStorage.removeItem(ACTIVE_SOURCE_KEY);
      }
    }
  }, [activeSourceId]);

  // Persist notes to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (notes) {
        window.sessionStorage.setItem(NOTES_KEY, notes);
      } else {
        window.sessionStorage.removeItem(NOTES_KEY);
      }
    }
  }, [notes]);

  // Persist quiz to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (quiz) {
        window.sessionStorage.setItem(QUIZ_KEY, quiz);
      } else {
        window.sessionStorage.removeItem(QUIZ_KEY);
      }
    }
  }, [quiz]);

  // Persist curriculum to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (curriculumSource) {
        window.sessionStorage.setItem(CURRICULUM_KEY, JSON.stringify(curriculumSource));
      } else {
        window.sessionStorage.removeItem(CURRICULUM_KEY);
      }
    }
  }, [curriculumSource]);

  // Persist curriculum chapter to sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (curriculumChapterNumber !== null) {
        window.sessionStorage.setItem(CURRICULUM_KEY + "_chapter", JSON.stringify(curriculumChapterNumber));
      } else {
        window.sessionStorage.removeItem(CURRICULUM_KEY + "_chapter");
      }
    }
  }, [curriculumChapterNumber]);

  // Clear curriculum selection when authenticated user changes
  // Curriculum sources are global/shared, but the selected curriculum is per-user session state
  useEffect(() => {
    if (typeof window === "undefined") return;
    // When user logs out or switches to a different user, clear the selected curriculum
    // but keep curriculumSources (they are global/shared content)
    setCurriculumActive(false);
    setCurriculumGrade(null);
    setCurriculumSource(null);
    setCurriculumChapterNumber(null);
    window.sessionStorage.removeItem(CURRICULUM_KEY);
    window.sessionStorage.removeItem(CURRICULUM_KEY + "_chapter");
  }, [user?.id]);

  const addSource = useCallback((source: SourceDocument) => {
    setSources((prev) => {
      const exists = prev.some((s) => s.id === source.id);
      if (exists) {
        return prev.map((s) => (s.id === source.id ? source : s));
      }
      return [...prev, source];
    });
  }, []);

  const setActiveSource = useCallback((sourceId: string | null) => {
    setActiveSourceId(sourceId);
  }, []);

  const removeSource = useCallback((sourceId: string) => {
    setSources((prev) => prev.filter((s) => s.id !== sourceId));
    if (activeSourceId === sourceId) {
      setActiveSourceId(null);
    }
  }, [activeSourceId]);

  const loadSources = useCallback(async () => {
    // Wait for auth loading to complete
    if (isLoading) {
      return;
    }
    
    // Only fetch sources if user is authenticated
    if (!user) {
      setSources([]);
      setActiveSourceId(null);
      return;
    }

    try {
      const accessToken = await getAccessToken();
      const backendSources = await listSources(accessToken);
      setSources(backendSources);
      if (activeSourceId && !backendSources.some((s) => s.id === activeSourceId)) {
        setActiveSourceId(null);
      }
    } catch (error) {
      console.error("Failed to load sources:", error);
    }
  }, [isLoading, user, activeSourceId, getAccessToken]);

  const loadCurriculumSources = useCallback(async () => {
    if (isLoading || !user) return;
    try {
      const accessToken = await getAccessToken();
      const backendCurriculum = await listCurriculumSources(accessToken);
      setCurriculumSources(backendCurriculum);
    } catch (error) {
      console.error("Failed to load curriculum sources:", error);
    }
  }, [isLoading, user, getAccessToken]);

  // Load curriculum sources when authenticated user becomes available
  // This ensures curriculum data loads even if UploadForge hasn't mounted yet
  useEffect(() => {
    if (!isLoading && user) {
      loadCurriculumSources();
    }
  }, [isLoading, user, loadCurriculumSources]);

  const setNotes = useCallback((value: string) => {
    setNotesState(value);
  }, []);

  const setQuiz = useCallback((value: string) => {
    setQuizState(value);
  }, []);

  const setCurriculumMode = useCallback<(
    active: boolean,
    grade?: number,
    source?: CurriculumSource | null,
    chapterNumber?: number | null
  ) => void>((active: boolean, grade?: number, source?: CurriculumSource | null, chapterNumber?: number | null): void => {
    setCurriculumActive(active);
    if (grade !== undefined) setCurriculumGrade(grade);
    if (source !== undefined) setCurriculumSource(source);
    if (chapterNumber !== undefined) setCurriculumChapterNumber(chapterNumber === 0 ? null : chapterNumber);
    if (!active) {
      setCurriculumGrade(null);
      setCurriculumSource(null);
      setCurriculumChapterNumber(null);
    }
  }, []);

  const clearAll = useCallback(() => {
    if (typeof window !== "undefined") {
      [SOURCES_KEY, ACTIVE_SOURCE_KEY, NOTES_KEY, QUIZ_KEY, CURRICULUM_KEY].forEach((k) =>
        window.sessionStorage.removeItem(k)
      );
      window.sessionStorage.removeItem(CURRICULUM_KEY + "_chapter");
    }
    setSources([]);
    setActiveSourceId(null);
    setNotesState(null);
    setQuizState(null);
    setCurriculumSources([]);
    setCurriculumActive(false);
    setCurriculumGrade(null);
    setCurriculumSource(null);
    setCurriculumChapterNumber(null);
  }, []);

  const value = useMemo<StudyContextValue>(
    () => ({
      sources,
      activeSourceId,
      notes,
      quiz,
      hasSources: sources.length > 0,
      addSource,
      setActiveSource,
      removeSource,
      loadSources,
      setNotes,
      setQuiz,
      clearAll,
      // Curriculum
      curriculumSources,
      curriculumActive,
      curriculumGrade,
      curriculumSource,
      curriculumChapterNumber,
      setCurriculumMode: setCurriculumMode as (active: boolean, grade?: number, source?: CurriculumSource | null, chapterNumber?: number | null) => void,
      loadCurriculumSources,
    }),
    [
      sources,
      activeSourceId,
      notes,
      quiz,
      curriculumSources,
      curriculumActive,
      curriculumGrade,
      curriculumSource,
      curriculumChapterNumber,
      addSource,
      setActiveSource,
      removeSource,
      loadSources,
      loadCurriculumSources,
      setNotes,
      setQuiz,
      setCurriculumMode,
      clearAll,
],
  ) as StudyContextValue;

  return <StudyContext.Provider value={value}>{children}</StudyContext.Provider>;
}

export function useStudy(): StudyContextValue {
  const ctx = useContext(StudyContext);
  if (!ctx) throw new Error("useStudy must be used within a StudyProvider");
  return ctx;
}
