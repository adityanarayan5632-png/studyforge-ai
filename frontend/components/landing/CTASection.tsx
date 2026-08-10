import { LinkButton } from "@/components/ui/Button";

export function CTASection() {
  return (
    <section className="border-t border-ink-700 bg-forge-grain px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-display text-3xl text-parchment-100 sm:text-4xl">
          Your notes are just sitting there.
        </h2>
        <p className="mt-3 text-parchment-500">
          Forge them into something you can actually study with.
        </p>
        <div className="mt-8">
          <LinkButton href="/signup" size="lg">
            Start forging — free
          </LinkButton>
        </div>
      </div>
    </section>
  );
}
