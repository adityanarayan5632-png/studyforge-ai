import { LinkButton } from "@/components/ui/Button";
import { Card, Badge } from "@/components/ui/Primitives";

const TIERS = [
  {
    name: "Scholar",
    price: "Free",
    description: "Everything you need to try the forge.",
    features: ["Unlimited PDF uploads", "AI tutor questions", "Notes & quiz generation"],
    highlighted: false,
  },
  {
    name: "Forgemaster",
    price: "$12/mo",
    description: "For heavier study seasons.",
    features: ["Everything in Scholar", "Priority processing", "Extended chat history"],
    highlighted: true,
  },
];

export function PricingTiers() {
  return (
    <section id="pricing" className="border-t border-ink-700 px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <p className="text-center font-data text-xs uppercase tracking-wide text-ember-400">
          Pricing
        </p>
        <h2 className="mt-3 text-center font-display text-3xl text-parchment-100">
          Pick your plan.
        </h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {TIERS.map((tier) => (
            <Card
              key={tier.name}
              className={`p-7 ${tier.highlighted ? "border-ember-500/60" : ""}`}
            >
              <div className="flex items-center justify-between">
                <h3 className="font-display text-xl text-parchment-100">{tier.name}</h3>
                {tier.highlighted && <Badge tone="ember">Popular</Badge>}
              </div>
              <p className="mt-3 font-display text-3xl text-parchment-100">{tier.price}</p>
              <p className="mt-1 text-sm text-parchment-500">{tier.description}</p>
              <ul className="mt-5 space-y-2 text-sm text-parchment-300">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <span className="mt-1 text-ember-400">&#9670;</span>
                    {f}
                  </li>
                ))}
              </ul>
              <LinkButton
                href="/signup"
                variant={tier.highlighted ? "primary" : "secondary"}
                className="mt-6 w-full"
              >
                Get started
              </LinkButton>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
