import type { Flashcard, QuizQuestion } from "./types";

/**
 * The backend has no dedicated flashcard endpoint and no structured quiz
 * endpoint — /generate-quiz returns raw LLM text shaped roughly like:
 *
 *   Question: ...
 *   A) ...
 *   B) ...
 *   C) ...
 *   D) ...
 *   Correct Answer: B
 *   Explanation: ...
 *
 * repeated ~10 times. This parser is intentionally forgiving about
 * whitespace, numbering, and minor formatting drift from the LLM.
 */

const OPTION_LABELS = ["A", "B", "C", "D"];

export function parseQuiz(raw: string): QuizQuestion[] {
  if (!raw?.trim()) return [];

  // Split on "Question" markers (with or without leading numbers/markdown).
  const blocks = raw
    .split(/(?=^\s*(?:\d+[.)]\s*)?\**Question\**\s*:?)/gim)
    .map((b) => b.trim())
    .filter(Boolean);

  const questions: QuizQuestion[] = [];

  for (const block of blocks) {
    const questionMatch = block.match(
      /Question\**\s*:?\s*([\s\S]*?)(?=\n\s*A[).]|\n\s*\**A\**\s*[).])/i
    );
    if (!questionMatch) continue;
    const questionText = questionMatch[1].trim();
    if (!questionText) continue;

    const options: { label: string; text: string }[] = [];
    for (let i = 0; i < OPTION_LABELS.length; i++) {
      const label = OPTION_LABELS[i];
      const nextLabel = OPTION_LABELS[i + 1];
      const pattern = nextLabel
        ? new RegExp(
            `\\**${label}\\**\\s*[).]\\s*([\\s\\S]*?)(?=\\n\\s*\\**${nextLabel}\\**\\s*[).]|\\n\\s*Correct)`,
            "i"
          )
        : new RegExp(`\\**${label}\\**\\s*[).]\\s*([\\s\\S]*?)(?=\\n\\s*Correct)`, "i");
      const match = block.match(pattern);
      if (match) {
        options.push({ label, text: match[1].trim() });
      }
    }
    if (options.length < 2) continue;

    const correctMatch = block.match(/Correct\s*Answer\**\s*:?\s*\**([A-D])/i);
    const correctLabel = correctMatch ? correctMatch[1].toUpperCase() : options[0].label;

    const explanationMatch = block.match(/Explanation\**\s*:?\s*([\s\S]*)/i);
    const explanation = explanationMatch ? explanationMatch[1].trim() : "";

    questions.push({
      id: crypto.randomUUID(),
      question: questionText,
      options,
      correctLabel,
      explanation,
    });
  }

  return questions;
}

/**
 * Flashcards are derived from parsed quiz questions since there's no
 * separate flashcard endpoint: front = question, back = correct answer
 * plus its explanation.
 */
export function quizToFlashcards(questions: QuizQuestion[]): Flashcard[] {
  return questions.map((q) => {
    const correctOption = q.options.find((o) => o.label === q.correctLabel);
    const answerText = correctOption
      ? `${correctOption.label}) ${correctOption.text}`
      : "See explanation";
    const back = q.explanation ? `${answerText}\n\n${q.explanation}` : answerText;
    return {
      id: q.id,
      front: q.question,
      back,
    };
  });
}
