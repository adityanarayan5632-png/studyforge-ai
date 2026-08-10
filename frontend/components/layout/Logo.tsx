import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="group inline-flex items-center gap-2">
      <svg
        width="26"
        height="26"
        viewBox="0 0 26 26"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        <path
          d="M13 2 L23 8 V18 L13 24 L3 18 V8 Z"
          stroke="var(--ember-500)"
          strokeWidth="1.5"
          fill="var(--ink-800)"
        />
        <path
          d="M13 8 L18 11.5 L13 15 L8 11.5 Z"
          fill="var(--ember-500)"
          className="transition-transform duration-300 group-hover:scale-110"
        />
        <path d="M13 15 V21" stroke="var(--ember-500)" strokeWidth="1.5" />
      </svg>
      <span className="font-display text-lg tracking-tight text-parchment-100">
        StudyForge <span className="text-ember-400">AI</span>
      </span>
    </Link>
  );
}
