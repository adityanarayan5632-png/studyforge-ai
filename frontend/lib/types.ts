export type SourceKind = "pdf" | "audio" | "video" | "image" | "youtube";

export interface SourceDocument {
  id: string;
  name: string;
  type: SourceKind;
  chunks?: number;
  createdAt: string;
}

export interface CurriculumSource {
  id: string;
  name: string;
  type: "curriculum";
  grade: number;
  subject: string;
  language: string;
  book_series: string;
  book_title: string;
  part: number;
  is_supplement: boolean;
  chapter?: string;
  chapter_number?: number;
  created_at: string;
}

export interface CurriculumBook {
  grade: number;
  subject: string;
  language: string;
  book_series: string;
  book_title: string;
  part: number;
  is_supplement: boolean;
  source_id: string;
  chapters: Array<{
    title: string;
    number: number;
  }>;
}

export interface UploadResponse {
  source_id: string;
  source_name: string;
  source_type: SourceKind;
  chunks_created: number;
  message: string;
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

export type Board = "CBSE" | "Other";

export interface StudentProfile {
  id: string;
  display_name: string;
  grade: 1 | 2 | 3 | 4 | 5;
  board: Board;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ConversationsResponse {
  conversations: Conversation[];
}

export interface ConversationWithMessages {
  conversation: Conversation;
  messages: Message[];
}

export interface MessagesResponse {
  messages: Message[];
}

export interface QuizAttempt {
  id: string;
  user_id: string;
  source_id: string | null;
  title: string | null;
  score: number;
  total_questions: number;
  percentage: number;
  created_at: string;
}

export interface QuizAttemptCreate {
  source_id?: string;
  title?: string;
  score: number;
  total_questions: number;
  percentage: number;
}

export interface QuizAttemptsResponse {
  quiz_attempts: QuizAttempt[];
}

export type StudyActivityType = 
  | "tutor_question"
  | "notes_generated"
  | "quiz_completed"
  | "source_uploaded"
  | "source_deleted";

export interface StudyActivity {
  id: string;
  user_id: string;
  activity_type: StudyActivityType;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface StudyActivityCreate {
  activity_type: StudyActivityType;
  metadata?: Record<string, unknown>;
}

export interface StudyActivitiesResponse {
  activities: StudyActivity[];
}

export type DashboardActivity = {
  id: string;
  activity_type: StudyActivityType;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export interface DashboardProfile {
  display_name: string | null;
  grade: number | null;
  board: string | null;
}

export interface DashboardConversation {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
  last_message_preview: string | null;
}

export interface DashboardQuizAttempt {
  id: string;
  title: string | null;
  score: number;
  total_questions: number;
  percentage: number;
  created_at: string;
}

export interface DashboardQuizPerformance {
  total_attempts: number;
  average_score: number;
  recent_attempts: DashboardQuizAttempt[];
}

export interface DashboardSummary {
  profile: {
    display_name: string | null;
    grade: number | null;
    board: string | null;
  };
  recent_conversation: DashboardConversation | null;
  quiz_performance: {
    total_attempts: number;
    average_score: number;
    recent_attempts: Array<{
      id: string;
      title: string | null;
      score: number;
      total_questions: number;
      percentage: number;
      created_at: string;
    }>;
  };
  recent_activities: Array<{
    id: string;
    activity_type: string;
    metadata: Record<string, unknown> | null;
    created_at: string;
  }>;
  recent_sources: Array<{
    id: string;
    name: string;
    type: string;
    created_at: string;
  }>;
  source_count: number;
}
