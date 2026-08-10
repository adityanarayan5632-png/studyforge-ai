export type SourceKind = "pdf" | "audio" | "video" | "image" | "youtube";

export interface UploadResponse {
  message: string;
  chunks_created: number;
}

export interface AskResponse {
  question: string;
  answer: string;
}

export interface NotesResponse {
  notes: string;
}

export interface QuizResponse {
  quiz: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: { label: string; text: string }[];
  correctLabel: string;
  explanation: string;
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
}

export type PlanTier = "scholar" | "forgemaster";

export interface StoredUser {
  id: string;
  name: string;
  email: string;
  plan: PlanTier;
  createdAt: number;
}
