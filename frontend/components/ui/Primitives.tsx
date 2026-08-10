import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-ink-600 bg-ink-900/80 backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "ember" | "ok" | "err";
}) {
  const tones: Record<string, string> = {
    default: "bg-ink-700 text-parchment-300 border-ink-500",
    ember: "bg-ember-500/15 text-ember-400 border-ember-500/40",
    ok: "bg-ok-500/15 text-ok-500 border-ok-500/40",
    err: "bg-err-500/15 text-err-500 border-err-500/40",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-data uppercase tracking-wide ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 rounded-full border-2 border-ember-500 border-t-transparent animate-spin ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-ink-500 px-6 py-14 text-center">
      <h3 className="font-display text-xl text-parchment-100">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-parchment-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return (
    <input
      className={`w-full rounded-md border border-ink-600 bg-ink-800 px-3.5 py-2.5 text-sm text-parchment-100 placeholder:text-parchment-700 outline-none transition-colors focus:border-ember-500 ${className}`}
      {...rest}
    />
  );
}

export function Label(props: LabelHTMLAttributes<HTMLLabelElement>) {
  const { className = "", ...rest } = props;
  return (
    <label
      className={`mb-1.5 block text-sm font-medium text-parchment-300 ${className}`}
      {...rest}
    />
  );
}
