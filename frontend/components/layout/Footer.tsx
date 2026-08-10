import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-ink-700 bg-ink-950">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
        <Logo />
        <p className="text-sm text-parchment-700">
          &copy; {new Date().getFullYear()} StudyForge AI. Forged, not templated.
        </p>
      </div>
    </footer>
  );
}
