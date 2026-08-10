"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const FILE_NAME_KEY = "studyforge:uploadedFileName";
const CHUNKS_KEY = "studyforge:chunksCreated";
const NOTES_KEY = "studyforge:notes";
const QUIZ_KEY = "studyforge:quiz";

interface StudyContextValue {
  uploadedFileName: string | null;
  chunksCreated: number | null;
  notes: string | null;
  quiz: string | null;
  hasUpload: boolean;
  setUpload: (fileName: string, chunksCreated: number) => void;
  setNotes: (notes: string) => void;
  setQuiz: (quiz: string) => void;
  clearAll: () => void;
}

const StudyContext = createContext<StudyContextValue | undefined>(undefined);

export function StudyProvider({ children }: { children: React.ReactNode }) {
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [chunksCreated, setChunksCreated] = useState<number | null>(null);
  const [notes, setNotesState] = useState<string | null>(null);
  const [quiz, setQuizState] = useState<string | null>(null);

  useEffect(() => {
    setUploadedFileName(window.sessionStorage.getItem(FILE_NAME_KEY));
    const chunks = window.sessionStorage.getItem(CHUNKS_KEY);
    setChunksCreated(chunks ? Number(chunks) : null);
    setNotesState(window.sessionStorage.getItem(NOTES_KEY));
    setQuizState(window.sessionStorage.getItem(QUIZ_KEY));
  }, []);

  const setUpload = useCallback((fileName: string, chunks: number) => {
    window.sessionStorage.setItem(FILE_NAME_KEY, fileName);
    window.sessionStorage.setItem(CHUNKS_KEY, String(chunks));
    setUploadedFileName(fileName);
    setChunksCreated(chunks);
  }, []);

  const setNotes = useCallback((value: string) => {
    window.sessionStorage.setItem(NOTES_KEY, value);
    setNotesState(value);
  }, []);

  const setQuiz = useCallback((value: string) => {
    window.sessionStorage.setItem(QUIZ_KEY, value);
    setQuizState(value);
  }, []);

  const clearAll = useCallback(() => {
    [FILE_NAME_KEY, CHUNKS_KEY, NOTES_KEY, QUIZ_KEY].forEach((k) =>
      window.sessionStorage.removeItem(k)
    );
    setUploadedFileName(null);
    setChunksCreated(null);
    setNotesState(null);
    setQuizState(null);
  }, []);

  const value = useMemo(
    () => ({
      uploadedFileName,
      chunksCreated,
      notes,
      quiz,
      hasUpload: Boolean(uploadedFileName),
      setUpload,
      setNotes,
      setQuiz,
      clearAll,
    }),
    [uploadedFileName, chunksCreated, notes, quiz, setUpload, setNotes, setQuiz, clearAll]
  );

  return <StudyContext.Provider value={value}>{children}</StudyContext.Provider>;
}

export function useStudy(): StudyContextValue {
  const ctx = useContext(StudyContext);
  if (!ctx) throw new Error("useStudy must be used within a StudyProvider");
  return ctx;
}
