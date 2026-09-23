import axios from "axios";
import type { AskResponse, NotesResponse, QuizResponse, UploadResponse, SourceDocument, SourceKind, Conversation, Message, ConversationsResponse, ConversationWithMessages, MessagesResponse, QuizAttempt, QuizAttemptCreate, QuizAttemptsResponse, StudyActivity, StudyActivityCreate, StudyActivitiesResponse, StudyActivityType, DashboardSummary, CurriculumSource } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function createApiClient(accessToken?: string | null) {
  return axios.create({
    baseURL: API_BASE_URL,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
}

export async function uploadFile(file: File, accessToken?: string | null): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const client = createApiClient(accessToken);
  const response = await client.post<UploadResponse>("/upload", formData);
  return response.data;
}

export async function uploadYoutubeLink(url: string, accessToken?: string | null): Promise<UploadResponse> {
  const client = createApiClient(accessToken);
  const response = await client.post<UploadResponse>("/upload-youtube", { url });
  return response.data;
}

export async function listSources(accessToken?: string | null): Promise<SourceDocument[]> {
  const client = createApiClient(accessToken);
  const response = await client.get<{ sources: Array<{
    source_id: string;
    source_name: string;
    source_type: string;
    created_at: string;
  }> }>("/sources");
  return response.data.sources.map((s) => ({
    id: s.source_id,
    name: s.source_name,
    type: s.source_type as SourceKind,
    chunks: undefined,
    createdAt: s.created_at,
  }));
}

export async function listCurriculumSources(accessToken?: string | null): Promise<CurriculumSource[]> {
  const client = createApiClient(accessToken);
  const response = await client.get<{ curriculum_sources: CurriculumSource[] }>("/sources");
  return response.data.curriculum_sources || [];
}

export async function deleteSource(sourceId: string, accessToken?: string | null): Promise<void> {
  const client = createApiClient(accessToken);
  await client.delete(`/sources/${sourceId}`);
}

export interface AskTutorOptions {
  useCurriculum?: boolean;
  grade?: number;
  curriculumSourceId?: string;
  chapterNumber?: number | null;
}

export async function askTutor(
  question: string,
  sourceId?: string,
  accessToken?: string | null,
  options?: AskTutorOptions
): Promise<AskResponse> {
  const params = new URLSearchParams({ question });
  if (sourceId) params.append("source_id", sourceId);
  if (options?.useCurriculum) params.append("use_curriculum", "true");
  if (options?.grade !== undefined) params.append("grade", String(options.grade));
  if (options?.curriculumSourceId) params.append("curriculum_source_id", options.curriculumSourceId);
  if (options?.chapterNumber !== undefined) params.append("chapter_number", String(options.chapterNumber));
  const client = createApiClient(accessToken);
  const response = await client.post<AskResponse>(
    `/ask?${params.toString()}`
  );
  return response.data;
}

export interface GenerateRequest {
  sourceId?: string | null;
  useCurriculum?: boolean;
  curriculumSourceId?: string | null;
  chapterNumber?: number | null;
}

export async function generateNotes(payload: GenerateRequest, accessToken?: string | null): Promise<NotesResponse> {
  const client = createApiClient(accessToken);
  const response = await client.post<NotesResponse>("/generate-notes", payload);
  return response.data;
}

export async function generateQuiz(payload: GenerateRequest, accessToken?: string | null): Promise<QuizResponse> {
  const client = createApiClient(accessToken);
  const response = await client.post<QuizResponse>("/generate-quiz", payload);
  return response.data;
}

// Conversation API
export async function listConversations(accessToken?: string | null): Promise<ConversationsResponse> {
  const client = createApiClient(accessToken);
  const response = await client.get<ConversationsResponse>("/conversations");
  return response.data;
}

export async function getConversation(conversationId: string, accessToken?: string | null): Promise<ConversationWithMessages> {
  const client = createApiClient(accessToken);
  const response = await client.get<ConversationWithMessages>(`/conversations/${conversationId}`);
  return response.data;
}

export async function createConversation(title: string, accessToken?: string | null): Promise<Conversation> {
  const client = createApiClient(accessToken);
  const response = await client.post<Conversation>("/conversations", { title });
  return response.data;
}

export async function updateConversation(conversationId: string, title: string, accessToken?: string | null): Promise<Conversation> {
  const client = createApiClient(accessToken);
  const response = await client.patch<Conversation>(`/conversations/${conversationId}`, { title });
  return response.data;
}

export async function deleteConversation(conversationId: string, accessToken?: string | null): Promise<{ message: string; conversation_id: string }> {
  const client = createApiClient(accessToken);
  const response = await client.delete(`/conversations/${conversationId}`);
  return response.data;
}

// Message API
export async function addMessage(conversationId: string, role: "user" | "assistant", content: string, accessToken?: string | null): Promise<Message> {
  const client = createApiClient(accessToken);
  const response = await client.post<Message>(`/conversations/${conversationId}/messages`, { role, content });
  return response.data;
}

export async function getMessages(conversationId: string, accessToken?: string | null): Promise<MessagesResponse> {
  const client = createApiClient(accessToken);
  const response = await client.get<MessagesResponse>(`/conversations/${conversationId}/messages`);
  return response.data;
}

// Quiz Attempt API
export async function createQuizAttempt(payload: QuizAttemptCreate, accessToken?: string | null): Promise<QuizAttempt> {
  const client = createApiClient(accessToken);
  const response = await client.post<QuizAttempt>("/quiz-attempts", payload);
  return response.data;
}

export async function listQuizAttempts(accessToken?: string | null): Promise<{ quiz_attempts: QuizAttempt[] }> {
  const client = createApiClient(accessToken);
  const response = await client.get<{ quiz_attempts: QuizAttempt[] }>("/quiz-attempts");
  return response.data;
}

export async function getQuizAttempt(attemptId: string, accessToken?: string | null): Promise<QuizAttempt> {
  const client = createApiClient(accessToken);
  const response = await client.get<QuizAttempt>(`/quiz-attempts/${attemptId}`);
  return response.data;
}

// Study Activity API
export async function createStudyActivity(payload: StudyActivityCreate, accessToken?: string | null): Promise<StudyActivity> {
  const client = createApiClient(accessToken);
  const response = await client.post<StudyActivity>("/study-activities", payload);
  return response.data;
}

export async function listStudyActivities(accessToken?: string | null): Promise<StudyActivitiesResponse> {
  const client = createApiClient(accessToken);
  const response = await client.get<StudyActivitiesResponse>("/study-activities");
  return response.data;
}

// Dashboard Summary API
export async function getDashboardSummary(accessToken?: string | null): Promise<DashboardSummary> {
  const client = createApiClient(accessToken);
  const response = await client.get<DashboardSummary>("/dashboard/summary");
  return response.data;
}
