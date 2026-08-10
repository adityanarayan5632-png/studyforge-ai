import axios from "axios";
import type { AskResponse, NotesResponse, QuizResponse, UploadResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<UploadResponse>("/upload", formData);
  return response.data;
}

export async function uploadYoutubeLink(url: string): Promise<UploadResponse> {
  const response = await apiClient.post<UploadResponse>("/upload-youtube", { url });
  return response.data;
}

export async function askTutor(question: string): Promise<AskResponse> {
  const response = await apiClient.post<AskResponse>(
    `/ask?question=${encodeURIComponent(question)}`
  );
  return response.data;
}

export async function generateNotes(): Promise<NotesResponse> {
  const response = await apiClient.post<NotesResponse>("/generate-notes");
  return response.data;
}

export async function generateQuiz(): Promise<QuizResponse> {
  const response = await apiClient.post<QuizResponse>("/generate-quiz");
  return response.data;
}
