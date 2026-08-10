import { Logo } from "@/components/layout/Logo";
import { Card } from "@/components/ui/Primitives";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <main className="relative flex min-h-screen items-center justify-center bg-ink-950 bg-forge-grain px-6 py-16">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <Card className="p-8">
          <h1 className="font-display text-2xl text-parchment-100">{title}</h1>
          <p className="mt-1.5 text-sm text-parchment-500">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </Card>
        <p className="mt-6 text-center text-sm text-parchment-500">{footer}</p>
      </div>
    </main>
  );
}
