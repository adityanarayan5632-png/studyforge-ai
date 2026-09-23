"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/auth/AuthShell";
import { Input, Label } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";

type Grade = 1 | 2 | 3 | 4 | 5;
type Board = "CBSE" | "Other";

const GRADES: Grade[] = [1, 2, 3, 4, 5];
const BOARDS: Board[] = ["CBSE", "Other"];

export default function OnboardingPage() {
  const [displayName, setDisplayName] = useState("");
  const [grade, setGrade] = useState<Grade | "">("");
  const [board, setBoard] = useState<Board | "">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { completeOnboarding } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!displayName.trim()) {
      setError("Display name is required.");
      return;
    }
    if (!grade) {
      setError("Please select a grade.");
      return;
    }
    if (!board) {
      setError("Please select a board.");
      return;
    }

    setLoading(true);
    try {
      await completeOnboarding({
        display_name: displayName.trim(),
        grade,
        board,
      });
      showToast("Welcome to StudyForge!", "success");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Complete your profile"
      subtitle="Help us personalize your study experience."
      footer={null}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="displayName">Display Name</Label>
          <Input
            id="displayName"
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="How should we call you?"
            maxLength={50}
          />
        </div>

        <div>
          <Label htmlFor="grade">Grade</Label>
          <div className="grid grid-cols-5 gap-2" role="radiogroup" aria-label="Select grade">
            {GRADES.map((g) => (
              <button
                key={g}
                type="button"
                role="radio"
                aria-checked={grade === g}
                onClick={() => setGrade(g)}
                className={`rounded-lg border-2 px-3 py-2.5 text-center text-sm font-medium transition-colors ${
                  grade === g
                    ? "border-ember-500 bg-ember-500/10 text-ember-400"
                    : "border-ink-600 text-parchment-300 hover:border-ink-500"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <div>
          <Label htmlFor="board">Board</Label>
          <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Select board">
            {BOARDS.map((b) => (
              <button
                key={b}
                type="button"
                role="radio"
                aria-checked={board === b}
                onClick={() => setBoard(b)}
                className={`rounded-lg border-2 px-3 py-2.5 text-center text-sm font-medium transition-colors ${
                  board === b
                    ? "border-ember-500 bg-ember-500/10 text-ember-400"
                    : "border-ink-600 text-parchment-300 hover:border-ink-500"
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-err-500">{error}</p>}
        <Button type="submit" className="w-full" loading={loading} size="lg">
          Continue to Dashboard
        </Button>
      </form>
    </AuthShell>
  );
}