import Link from "next/link";
import { Card } from "@/components/ui/Primitives";

const ACTIONS = [
  {
    href: "/dashboard/tutor",
    title: "Ask the tutor",
    description: "Question your material directly and get grounded answers.",
  },
  {
    href: "/dashboard/notes",
    title: "Generate notes",
    description: "Turn your material into a structured summary and key points.",
  },
  {
    href: "/dashboard/study",
    title: "Quiz & flashcards",
    description: "Test yourself with generated multiple choice questions.",
  },
];

export function QuickActions() {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {ACTIONS.map((action) => (
        <Link key={action.href} href={action.href}>
          <Card className="h-full p-5 transition-colors hover:border-ember-500/50">
            <h3 className="font-display text-base text-parchment-100">{action.title}</h3>
            <p className="mt-1.5 text-sm text-parchment-500">{action.description}</p>
            <span className="mt-3 inline-block text-sm font-medium text-ember-400">
              Open &rarr;
            </span>
          </Card>
        </Link>
      ))}
    </div>
  );
}
