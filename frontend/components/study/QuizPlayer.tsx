"use client";

import { useMemo, useState, useEffect } from "react";
import { Card, Badge } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import type { QuizQuestion } from "@/lib/types";

export function QuizPlayer({ 
  questions, 
  onComplete 
}: { 
  questions: QuizQuestion[];
  onComplete?: (score: number, total: number, percentage: number) => void;
}) {
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});

  const question = questions[current];
  const score = useMemo(
    () =>
      questions.filter((q) => selected[q.id] && selected[q.id] === q.correctLabel).length,
    [questions, selected]
  );
  const answeredCount = Object.keys(revealed).length;
  const allAnswered = answeredCount === questions.length && questions.length > 0;

  const pick = (label: string) => {
    if (revealed[question.id]) return;
    setSelected((prev) => ({ ...prev, [question.id]: label }));
    setRevealed((prev) => ({ ...prev, [question.id]: true }));
  };

  // Trigger onComplete when all questions are answered
  useEffect(() => {
    if (allAnswered && onComplete && questions.length > 0) {
      const finalScore = score;
      const total = questions.length;
      const percentage = Math.round((score / questions.length) * 100);
      onComplete(finalScore, total, percentage);
    }
  }, [allAnswered, onComplete, questions, score]);

  if (questions.length === 0 || !questions[current]) return null;

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <Badge>
          Question {current + 1} / {questions.length}
        </Badge>
        <Badge tone="ember">
          Score {score} / {answeredCount}
        </Badge>
      </div>

      <h3 className="mt-4 font-display text-lg text-parchment-100">{question.question}</h3>

      <div className="mt-5 flex flex-col gap-2.5">
        {question.options.map((option) => {
          const isSelected = selected[question.id] === option.label;
          const isCorrect = option.label === question.correctLabel;
          const showState = revealed[question.id];

          let stateClasses = "border-ink-600 hover:border-ember-500/60";
          if (showState && isCorrect) {
            stateClasses = "border-ok-500 bg-ok-500/10 text-ok-500";
          } else if (showState && isSelected && !isCorrect) {
            stateClasses = "border-err-500 bg-err-500/10 text-err-500";
          }

          return (
            <button
              key={option.label}
              onClick={() => pick(option.label)}
              disabled={showState}
              className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-left text-sm transition-colors disabled:cursor-default ${stateClasses}`}
            >
              <span className="font-data text-xs text-parchment-500">{option.label}</span>
              <span>{option.text}</span>
            </button>
          );
        })}
      </div>

      {revealed[question.id] && question.explanation && (
        <p className="mt-4 rounded-lg bg-ink-800 p-3 text-sm text-parchment-300">
          {question.explanation}
        </p>
      )}

      <div className="mt-6 flex justify-between">
        <Button
          variant="secondary"
          size="sm"
          disabled={current === 0}
          onClick={() => setCurrent((c) => Math.max(0, c - 1))}
        >
          Previous
        </Button>
        <Button
          size="sm"
          disabled={current === questions.length - 1}
          onClick={() => setCurrent((c) => Math.min(questions.length - 1, c + 1))}
        >
          Next
        </Button>
      </div>
    </Card>
  );
}