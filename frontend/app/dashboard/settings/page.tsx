"use client";

import { Card, Badge, Label, Input } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";
import { useStudy } from "@/lib/study-context";
import { useToast } from "@/components/ui/Toast";
import type { PlanTier } from "@/lib/types";

const PLANS: { id: PlanTier; name: string; price: string }[] = [
  { id: "scholar", name: "Scholar", price: "Free" },
  { id: "forgemaster", name: "Forgemaster", price: "$12/mo" },
];

export default function SettingsPage() {
  const { user, setPlan } = useAuth();
  const { clearAll } = useStudy();
  const { showToast } = useToast();

  if (!user) return null;

  const handleClearSession = () => {
    clearAll();
    showToast("Session data cleared.", "success");
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card className="p-6">
        <h2 className="font-display text-lg text-parchment-100">Account</h2>
        <div className="mt-4 space-y-4">
          <div>
            <Label>Name</Label>
            <Input value={user.name} disabled />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={user.email} disabled />
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-lg text-parchment-100">Plan</h2>
        <p className="mt-1 text-sm text-parchment-500">Switch between tiers at any time.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {PLANS.map((plan) => {
            const active = user.plan === plan.id;
            return (
              <button
                key={plan.id}
                onClick={() => {
                  setPlan(plan.id);
                  showToast(`Switched to ${plan.name}.`, "success");
                }}
                className={`rounded-lg border px-4 py-3.5 text-left transition-colors ${
                  active ? "border-ember-500 bg-ember-500/10" : "border-ink-600 hover:border-ink-500"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-parchment-100">{plan.name}</span>
                  {active && <Badge tone="ember">Current</Badge>}
                </div>
                <span className="mt-1 block text-sm text-parchment-500">{plan.price}</span>
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-lg text-parchment-100">Session data</h2>
        <p className="mt-1 text-sm text-parchment-500">
          Clears your uploaded file reference, generated notes, and quiz from this browser.
          This doesn&apos;t touch anything on the backend.
        </p>
        <Button variant="danger" className="mt-4" onClick={handleClearSession}>
          Clear session data
        </Button>
      </Card>
    </div>
  );
}
