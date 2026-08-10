"use client";

import { useState } from "react";
import { Card, Badge } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import type { Flashcard } from "@/lib/types";

export function FlashcardDeck({ cards }: { cards: Flashcard[] }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const card = cards[index];
  if (!card) return null;

  const goTo = (next: number) => {
    setIndex(Math.max(0, Math.min(cards.length - 1, next)));
    setFlipped(false);
  };

  return (
    <div>
      <div className="flex justify-center">
        <Badge>
          Card {index + 1} / {cards.length}
        </Badge>
      </div>

      <button
        onClick={() => setFlipped((f) => !f)}
        className="mt-4 block w-full text-left"
        aria-label="Flip card"
      >
        <Card className="flex min-h-[220px] items-center justify-center p-8 text-center transition-colors hover:border-ember-500/50">
          <div>
            {!flipped ? (
              <>
                <p className="mb-2 font-data text-xs uppercase tracking-wide text-parchment-700">
                  Question
                </p>
                <p className="font-display text-lg text-parchment-100">{card.front}</p>
              </>
            ) : (
              <>
                <p className="mb-2 font-data text-xs uppercase tracking-wide text-ember-400">
                  Answer
                </p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-parchment-300">
                  {card.back}
                </p>
              </>
            )}
            <p className="mt-4 text-xs text-parchment-700">Click to flip</p>
          </div>
        </Card>
      </button>

      <div className="mt-5 flex justify-between">
        <Button variant="secondary" size="sm" disabled={index === 0} onClick={() => goTo(index - 1)}>
          Previous
        </Button>
        <Button size="sm" disabled={index === cards.length - 1} onClick={() => goTo(index + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
