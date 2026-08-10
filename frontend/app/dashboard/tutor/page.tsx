"use client";

import { useState } from "react";
import { ChatThread } from "@/components/tutor/ChatThread";
import { Card, EmptyState } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { askTutor } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useToast } from "@/components/ui/Toast";
import type { ChatMessage } from "@/lib/types";

export default function TutorPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const { hasUpload, uploadedFileName } = useStudy();
  const { showToast } = useToast();

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || pending) return;

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
      const result = await askTutor(trimmed);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.answer,
          createdAt: Date.now(),
        },
      ]);
    } catch (error) {
      console.error(error);
      showToast("Couldn't reach the tutor. Is the backend running?", "error");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      {!hasUpload && (
        <p className="mb-4 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-parchment-500">
          No PDF uploaded yet this session — the tutor will answer based on whatever material
          is already in the backend&apos;s store.
        </p>
      )}
      {uploadedFileName && (
        <p className="mb-4 font-data text-xs text-parchment-700">
          Grounded in: {uploadedFileName}
        </p>
      )}

      <Card className="flex flex-1 flex-col p-6">
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState
              title="Ask anything from your material"
              description="Try: 'Summarize chapter 2' or 'What's the difference between X and Y?'"
            />
          ) : (
            <ChatThread messages={messages} pending={pending} />
          )}
        </div>

        <form onSubmit={handleAsk} className="mt-5 flex gap-2 border-t border-ink-700 pt-5">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question from your uploaded PDF..."
            className="flex-1 rounded-md border border-ink-600 bg-ink-800 px-3.5 py-2.5 text-sm text-parchment-100 placeholder:text-parchment-700 outline-none focus:border-ember-500"
          />
          <Button type="submit" loading={pending} disabled={!question.trim()}>
            Ask
          </Button>
        </form>
      </Card>
    </div>
  );
}
