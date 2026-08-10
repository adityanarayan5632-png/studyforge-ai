const STEPS = [
  {
    step: "01",
    title: "Upload your PDF",
    description: "Drop in lecture slides, a textbook chapter, or your own notes.",
  },
  {
    step: "02",
    title: "It gets chunked & embedded",
    description: "Your material is split and indexed so it can be searched precisely.",
  },
  {
    step: "03",
    title: "Study your way",
    description: "Ask the tutor, generate notes, or take a quiz — all grounded in that upload.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-ink-700 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <p className="font-data text-xs uppercase tracking-wide text-ember-400">
          How it works
        </p>
        <h2 className="mt-3 font-display text-3xl text-parchment-100">
          Three steps, in order.
        </h2>
        <div className="mt-10 grid gap-8 sm:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.step}>
              <span className="font-display text-4xl text-ink-500">{s.step}</span>
              <h3 className="mt-3 font-display text-lg text-parchment-100">{s.title}</h3>
              <p className="mt-2 text-sm text-parchment-500">{s.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
