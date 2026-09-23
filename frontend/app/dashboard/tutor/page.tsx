"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatThread } from "@/components/tutor/ChatThread";
import { Card, EmptyState } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { askTutor, listConversations, createConversation, getConversation, addMessage } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import type { ChatMessage, Conversation, CurriculumSource } from "@/lib/types";

export default function TutorPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const { sources, activeSourceId, hasSources, curriculumActive, curriculumGrade, curriculumSource, curriculumChapterNumber, setCurriculumMode } = useStudy();
  const { getAccessToken, profile } = useAuth();
  const { showToast } = useToast();

  // Load conversations on mount
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const token = await getAccessToken();
        const result = await listConversations(token);
        setConversations(result.conversations);

        // If there are existing conversations, load the most recent one
        if (result.conversations.length > 0) {
          const latestConv = result.conversations[0];
          const convResult = await getConversation(latestConv.id, token);
          setConversationId(latestConv.id);
          // Convert backend messages to ChatMessage format
          const chatMessages: ChatMessage[] = convResult.messages.map((msg) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            createdAt: new Date(msg.created_at).getTime(),
          }));
          setMessages(chatMessages);
        }
      } catch (error) {
        console.error("Failed to load conversations:", error);
      }
    };
    loadConversations();
  }, [getAccessToken]);

  // Create a new conversation
  const createNewConversation = useCallback(async () => {
    try {
      const token = await getAccessToken();
      const conv = await createConversation("New Conversation", token);
      setConversationId(conv.id);
      setMessages([]);
      const token2 = await getAccessToken();
      const result = await listConversations(token2);
      setConversations(result.conversations);
    } catch (error) {
      console.error("Failed to create conversation:", error);
      showToast("Couldn't create conversation", "error");
    }
  }, [getAccessToken, showToast]);

const handleChapterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = Number(e.target.value);
    const chapterNum = val === 0 ? undefined : val;
    setCurriculumMode(true, curriculumGrade ?? undefined, curriculumSource, chapterNum);
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    // Create conversation if none exists
    if (!conversationId) {
      await createNewConversation();
      // Wait for conversationId to be set
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setPending(true);

    try {
      // Save user message to conversation
      const token = await getAccessToken();
      await addMessage(conversationId!, "user", trimmed, token);

      let result;
      if (curriculumActive) {
        // Curriculum mode
        const grade = curriculumGrade ?? profile?.grade ?? 1;
        result = await askTutor(trimmed, undefined, token, {
          useCurriculum: true,
          grade,
          curriculumSourceId: curriculumSource?.id,
          chapterNumber: curriculumChapterNumber ?? undefined
        });
      } else {
        // User source mode
        result = await askTutor(trimmed, activeSourceId || undefined, token);
      }

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer,
        createdAt: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Save assistant response to conversation
      await addMessage(conversationId!, "assistant", result.answer, token);
    } catch (error) {
      console.error(error);
      showToast("Couldn't reach the tutor. Is the backend running?", "error");
    } finally {
      setPending(false);
    }
  };

  const activeSource = sources.find((s) => s.id === activeSourceId);

  // Determine display mode
  const isCurriculumMode = curriculumActive;
  const displaySource = isCurriculumMode ? curriculumSource : activeSource;
  const curriculumLabel = isCurriculumMode && displaySource
    ? ` — ${(displaySource as CurriculumSource).book_title} (${(displaySource as CurriculumSource).chapter ? `Ch ${(displaySource as CurriculumSource).chapter_number}` : `Part ${(displaySource as CurriculumSource).part}`}${curriculumChapterNumber ? ` → Ch ${curriculumChapterNumber}` : ""})`
    : "";
  const displayMode = isCurriculumMode
    ? `Curriculum Mode: Grade ${curriculumGrade ?? profile?.grade ?? 1}${curriculumLabel}`
    : activeSourceId
      ? `Grounded in: ${activeSource?.name} (${activeSource?.type})`
      : hasSources
        ? `Mode: Global — searching all ${sources.length} source${sources.length > 1 ? "s" : ""}`
        : null;

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      {!hasSources && !isCurriculumMode && (
        <p className="mb-4 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-parchment-500">
          No sources uploaded yet — the tutor will answer based on whatever material
          is already in the backend&apos;s store.
        </p>
      )}
      {displayMode && (
        <p className="mb-4 font-data text-xs text-parchment-700">
          {displayMode}
        </p>
      )}

      <Card className="flex flex-1 flex-col p-6">
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !conversationId ? (
            <EmptyState
              title="Ask anything from your material"
              description="Try: 'Summarize chapter 2' or 'What's the difference between X and Y?'"
              action={
                <Button onClick={createNewConversation}>
                  Start a conversation
                </Button>
              }
            />
          ) : messages.length === 0 ? (
            <EmptyState
              title="New conversation"
              description="Ask your first question to get started"
            />
          ) : (
            <ChatThread messages={messages} pending={pending} />
          )}
        </div>

        {conversationId && (
          <div className="mt-4 flex items-center justify-between">
            <span className="font-data text-xs text-parchment-500">
              {conversations.find(c => c.id === conversationId)?.title || "Conversation"}
            </span>
            <Button variant="ghost" size="sm" onClick={createNewConversation}>
              New conversation
            </Button>
          </div>
        )}

        {/* Curriculum mode toggle */}
        <div className="mt-4 flex flex-col gap-3 border-t border-ink-700 pt-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={curriculumActive}
              onChange={(e) => setCurriculumMode(e.target.checked, profile?.grade ?? 1, curriculumSource)}
              className="rounded border-ink-600 text-ember-500 focus:ring-ember-500"
            />
            <span className="text-sm text-parchment-300">Curriculum mode</span>
          </label>
          {curriculumActive && (
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={curriculumGrade ?? profile?.grade ?? 1}
                onChange={(e) => setCurriculumMode(true, Number(e.target.value), curriculumSource)}
                className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5 text-sm text-parchment-100 outline-none focus:border-ember-500"
              >
                {[1, 2, 3, 4, 5].map((g) => (
                  <option key={g} value={g}>Grade {g}</option>
                ))}
              </select>
              {curriculumSource && (
                <select
                  value={curriculumChapterNumber ?? 0}
                  onChange={handleChapterChange}
                  className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5 text-sm text-parchment-100 outline-none focus:border-ember-500"
                >
                  <option value={0}>All chapters</option>
                  {(curriculumSource.chapter_number ? Array.from({ length: curriculumSource.chapter_number }, (_, i) => i + 1) : [1]).map((ch) => (
                    <option key={ch} value={ch}>Chapter {ch}</option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>

        <form onSubmit={handleAsk} className="mt-5 flex gap-2 border-t border-ink-700 pt-5">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={conversationId
              ? (isCurriculumMode
                  ? "Ask a question from curriculum..."
                  : (activeSourceId ? "Ask a question from the selected source..." : "Ask a question from all sources..."))
              : "Start a conversation to ask a question..."}
            disabled={!conversationId}
            className="flex-1 rounded-md border border-ink-600 bg-ink-800 px-3.5 py-2.5 text-sm text-parchment-100 placeholder:text-parchment-700 outline-none focus:border-ember-500 disabled:opacity-50"
          />
          <Button type="submit" loading={pending} disabled={!question.trim() || !conversationId || pending}>
            Ask
          </Button>
        </form>
      </Card>
    </div>
  );
}
