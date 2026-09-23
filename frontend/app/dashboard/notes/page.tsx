"use client";

import { useState } from "react";
import { Card, EmptyState } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { NotesViewer } from "@/components/notes/NotesViewer";
import { generateNotes, type GenerateRequest } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";

export default function NotesPage() {
  const [loading, setLoading] = useState(false);
  const { notes, setNotes, sources, activeSourceId, hasSources, curriculumActive, curriculumSource, curriculumChapterNumber } = useStudy();
  const { getAccessToken } = useAuth();
  const { showToast } = useToast();

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const accessToken = await getAccessToken();

      const payload: GenerateRequest = curriculumActive
        ? {
            useCurriculum: true,
            curriculumSourceId: curriculumSource?.id,
            chapterNumber: curriculumChapterNumber ?? null,
          }
        : {
            sourceId: activeSourceId,
          };

      const result = await generateNotes(payload, accessToken);
      setNotes(result.notes);
      showToast("Notes generated.", "success");
    } catch (error) {
      console.error(error);
      showToast("Couldn't generate notes. Is the backend running?", "error");
    } finally {
      setLoading(false);
    }
  };

  const activeSource = sources.find((s) => s.id === activeSourceId);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-parchment-100">Study notes</h2>
          {activeSourceId && (
            <p className="mt-1 font-data text-xs text-parchment-700">
              Source: {activeSource?.name} ({activeSource?.type})
            </p>
          )}
          {!activeSourceId && hasSources && (
            <p className="mt-1 font-data text-xs text-parchment-700">
              Mode: Global — using all {sources.length} source{sources.length > 1 ? "s" : ""}
            </p>
          )}
        </div>
        <Button onClick={handleGenerate} loading={loading}>
          {notes ? "Regenerate notes" : "Generate notes"}
        </Button>
      </div>

      <Card className="mt-5 p-6">
        {notes ? (
          <NotesViewer raw={notes} />
        ) : (
          <EmptyState
            title="No notes yet"
            description="Generate a structured summary, key concepts, and revision points from your material."
            action={
              <Button onClick={handleGenerate} loading={loading}>
                Generate notes
              </Button>
            }
          />
        )}
      </Card>
    </div>
  );
}
