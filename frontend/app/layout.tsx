import type { Metadata } from "next";
import "@fontsource-variable/fraunces";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { StudyProvider } from "@/lib/study-context";
import { ToastProvider } from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "StudyForge AI — Turn your notes into mastery",
  description:
    "Upload a PDF and forge it into an AI tutor, study notes, quizzes, and flashcards.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-ink-950 text-parchment-100">
        <ToastProvider>
          <AuthProvider>
            <StudyProvider>{children}</StudyProvider>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
