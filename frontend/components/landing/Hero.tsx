import { LinkButton } from "@/components/ui/Button";

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-forge-grain px-6 pt-24 pb-20">
      <div className="mx-auto max-w-4xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-ink-600 bg-ink-800/60 px-3.5 py-1.5 font-data text-xs uppercase tracking-wide text-ember-400">
          <span className="h-1.5 w-1.5 rounded-full bg-ember-500 animate-ember-pulse" />
          Upload once. Study every way.
        </div>
        <h1 className="font-display text-5xl leading-[1.08] text-parchment-100 sm:text-6xl">
          Drop in a PDF.
          <br />
          Pull out a <span className="text-ember-400">tutor, notes,</span> and a quiz.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-parchment-500">
          StudyForge AI reads your material once, then lets you question it, summarize it,
          and test yourself on it — grounded in exactly what you gave it.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <LinkButton href="/signup" size="lg">
            Start forging — free
          </LinkButton>
          <LinkButton href="#how-it-works" variant="secondary" size="lg">
            See how it works
          </LinkButton>
        </div>
      </div>

      <div className="mx-auto mt-16 max-w-3xl rounded-xl border border-ink-600 bg-ink-900 p-5 font-data text-sm shadow-2xl shadow-black/40">
        <div className="flex items-center gap-1.5 pb-3">
          <span className="h-2.5 w-2.5 rounded-full bg-err-500/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-ember-500/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-ok-500/60" />
        </div>
        <p className="text-parchment-500">
          <span className="text-ember-400">&gt;</span> ask &quot;what causes the Krebs cycle to
          slow down?&quot;
        </p>
        <p className="mt-2 text-parchment-300">
          Based on chapter 4 of your uploaded notes: the Krebs cycle slows when NADH
          accumulates and inhibits isocitrate dehydrogenase...
        </p>
      </div>
    </section>
  );
}
