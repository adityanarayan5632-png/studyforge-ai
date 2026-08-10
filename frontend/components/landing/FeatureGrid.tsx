import { Card } from "@/components/ui/Primitives";

const FEATURES = [
  {
    title: "AI Tutor",
    description:
      "Ask direct questions about your material and get answers grounded in what you uploaded — not generic web knowledge.",
  },
  {
    title: "Structured notes",
    description:
      "A clean summary, key concepts, definitions, and revision points generated straight from your PDF.",
  },
  {
    title: "Quiz & flashcards",
    description:
      "Multiple choice questions with explanations, automatically turned into a flippable flashcard deck too.",
  },
];

export function FeatureGrid() {
  return (
    <section id="features" className="border-t border-ink-700 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="max-w-xl">
          <p className="font-data text-xs uppercase tracking-wide text-ember-400">Features</p>
          <h2 className="mt-3 font-display text-3xl text-parchment-100">
            One upload, three tools.
          </h2>
        </div>
        <div className="mt-10 grid gap-5 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="p-6">
              <h3 className="font-display text-lg text-parchment-100">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-parchment-500">
                {feature.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
