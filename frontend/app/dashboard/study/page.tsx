"use client";

import { useMemo, useState } from "react";
import { Card, EmptyState } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { QuizPlayer } from "@/components/study/QuizPlayer";
import { FlashcardDeck } from "@/components/study/FlashcardDeck";
import { generateQuiz } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useToast } from "@/components/ui/Toast";
import { parseQuiz, quizToFlashcards } from "@/lib/parseQuiz";

type Tab = "quiz" | "flashcards";

export default function StudyPage() {
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("quiz");
  const { quiz, setQuiz, uploadedFileName } = useStudy();
  const { showToast } = useToast();

  const questions = useMemo(() => (quiz ? parseQuiz(quiz) : []), [quiz]);
  const flashcards = useMemo(() => quizToFlashcards(questions), [questions]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await generateQuiz();
      setQuiz(result.quiz);
      showToast("Quiz generated.", "success");
    } catch (error) {
      console.error(error);
      showToast("Couldn't generate a quiz. Is the backend running?", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-parchment-100">Quiz & flashcards</h2>
          {uploadedFileName && (
            <p className="mt-1 font-data text-xs text-parchment-700">
              Source: {uploadedFileName}
            </p>
          )}
        </div>
        <Button onClick={handleGenerate} loading={loading}>
          {quiz ? "Regenerate quiz" : "Generate quiz"}
        </Button>
      </div>

      {questions.length > 0 && (
        <div className="mt-5 inline-flex rounded-md border border-ink-600 bg-ink-800 p-1">
          {(["quiz", "flashcards"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-ember-500 text-ink-950" : "text-parchment-500 hover:text-parchment-100"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <div className="mt-5">
        {questions.length === 0 ? (
          <Card className="p-6">
            <EmptyState
              title="No quiz yet"
              description="Generate a 10-question multiple choice quiz from your uploaded material — it also unlocks a flashcard deck."
              action={
                <Button onClick={handleGenerate} loading={loading}>
                  Generate quiz
                </Button>
              }
            />
          </Card>
        ) : tab === "quiz" ? (
          <QuizPlayer questions={questions} />
        ) : (
          <Card className="p-6">
            <FlashcardDeck cards={flashcards} />
          </Card>
        )}
      </div>
    </div>
  );
}
