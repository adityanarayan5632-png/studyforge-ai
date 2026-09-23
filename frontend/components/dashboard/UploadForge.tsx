"use client";

import { useEffect, useRef, useState } from "react";
import { Card, Badge, Input } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { uploadFile, uploadYoutubeLink, deleteSource } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import type { SourceKind, SourceDocument, CurriculumSource } from "@/lib/types";

const SOURCE_TABS: { id: SourceKind; label: string; accept?: string; hint: string }[] = [
  { id: "pdf", label: "PDF", accept: "application/pdf", hint: "PDF documents" },
  {
    id: "audio",
    label: "Audio",
    accept: "audio/mpeg,audio/wav,audio/mp4,audio/ogg,audio/flac,audio/aac,.mp3,.wav,.m4a,.ogg,.flac,.aac",
    hint: "mp3, wav, m4a, ogg, flac, aac — transcribed automatically",
  },
  {
    id: "video",
    label: "Video",
    accept: "video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm,.mp4,.mov,.avi,.mkv,.webm",
    hint: "mp4, mov, avi, mkv, webm — audio track is transcribed",
  },
  {
    id: "image",
    label: "Screenshot",
    accept: "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp",
    hint: "png, jpg, webp — text is read via OCR",
  },
  { id: "youtube", label: "YouTube link", hint: "Captions used if available, otherwise transcribed" },
];

function buildCurriculumHierarchy(sources: CurriculumSource[]) {
  const hierarchy: Record<number, Record<string, Record<string, Record<string, CurriculumSource[]>>>> = {};

  for (const src of sources) {
    if (!src.grade || !src.subject || !src.book_series || !src.book_title) continue;
    const grade = src.grade;
    const subject = src.subject;
    const series = src.book_series;
    const book = src.book_title;
    if (!hierarchy[grade]) hierarchy[grade] = {};
    if (!hierarchy[grade][subject]) hierarchy[grade][subject] = {};
    if (!hierarchy[grade][subject][series]) hierarchy[grade][subject][series] = {};
    if (!hierarchy[grade][subject][series][book]) hierarchy[grade][subject][series][book] = [];
    hierarchy[grade][subject][series][book].push(src);
  }

  return hierarchy;
}

export function UploadForge() {
  const [activeTab, setActiveTab] = useState<SourceKind>("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { sources, activeSourceId, addSource, setActiveSource, removeSource, curriculumSources, curriculumActive, curriculumGrade, curriculumSource, curriculumChapterNumber, setCurriculumMode, loadCurriculumSources } = useStudy();
  const { getAccessToken, profile } = useAuth();
  const { showToast } = useToast();

  const activeConfig = SOURCE_TABS.find((t) => t.id === activeTab)!;

  useEffect(() => {
    loadCurriculumSources();
  }, [loadCurriculumSources]);

  const switchTab = (tab: SourceKind) => {
    setActiveTab(tab);
    setFile(null);
    setYoutubeUrl("");
  };

  const handleFiles = (files: FileList | null) => {
    const picked = files?.[0];
    if (picked) setFile(picked);
  };

  const handleUpload = async () => {
    const accessToken = await getAccessToken();
    setLoading(true);
    try {
      if (activeTab === "youtube") {
        const trimmed = youtubeUrl.trim();
        if (!trimmed) {
          showToast("Paste a YouTube link first.", "error");
          return;
        }
        const result = await uploadYoutubeLink(trimmed, accessToken);
        const source: SourceDocument = {
          id: result.source_id,
          name: result.source_name,
          type: result.source_type,
          chunks: result.chunks_created,
          createdAt: new Date().toISOString(),
        };
        addSource(source);
        setActiveSource(source.id);
        showToast(result.message || "YouTube video processed.", "success");
      } else {
        if (!file) {
          showToast(`Choose ${activeConfig.label === "PDF" ? "a" : "an"} ${activeConfig.label.toLowerCase()} file first.`, "error");
          return;
        }
        const result = await uploadFile(file, accessToken);
        const source: SourceDocument = {
          id: result.source_id,
          name: result.source_name,
          type: result.source_type,
          chunks: result.chunks_created,
          createdAt: new Date().toISOString(),
        };
        addSource(source);
        setActiveSource(source.id);
        showToast(result.message || "Uploaded and processed.", "success");
      }
    } catch (error) {
      console.error(error);
      showToast("Processing failed. Is the backend running?", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    const accessToken = await getAccessToken();
    try {
      await deleteSource(sourceId, accessToken);
      removeSource(sourceId);
      showToast("Source deleted.", "success");
    } catch (error) {
      console.error(error);
      showToast("Failed to delete source.", "error");
    }
  };

  const handleCurriculumSelect = (source: CurriculumSource, chapterNumber?: number | null) => {
    const grade = source.grade ?? profile?.grade ?? 1;
    setCurriculumMode(true, grade, source, chapterNumber);
    const chapterLabel = chapterNumber ? ` Ch ${chapterNumber}` : "";
    showToast(`Curriculum: ${source.book_title}${chapterLabel} (Grade ${grade})`, "success");
  };

  const handleCurriculumClear = () => {
    setCurriculumMode(false);
    showToast("Curriculum mode cleared.", "success");
  };

  const hierarchy = buildCurriculumHierarchy(curriculumSources);
  const grades = Object.keys(hierarchy).map(Number).sort((a, b) => a - b);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg text-parchment-100">Feed the forge</h2>
        {sources.length > 0 && <Badge tone="ok">{sources.length} source{sources.length > 1 ? "s" : ""} loaded</Badge>}
      </div>
      <p className="mt-1 text-sm text-parchment-500">
        Upload a source — PDF, audio, video, a screenshot, or a YouTube link. It gets turned
        into text, chunked, and embedded so the tutor, notes, and quiz can draw from it.
      </p>

      <div className="mt-4 flex flex-wrap gap-1 rounded-md border border-ink-600 bg-ink-800 p-1">
        {SOURCE_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => switchTab(tab.id)}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-ember-500 text-ink-950"
                : "text-parchment-500 hover:text-parchment-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="mt-2 font-data text-xs text-parchment-700">{activeConfig.hint}</p>

      {activeTab === "youtube" ? (
        <div className="mt-4">
          <Input
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
          />
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            isDragging ? "border-ember-500 bg-ember-500/5" : "border-ink-600 hover:border-ink-500"
          }`}
        >
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="mb-3">
            <path
              d="M16 4v16m0 0-6-6m6 6 6-6M6 24v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2"
              stroke="var(--ember-500)"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-sm text-parchment-300">
            {file ? file.name : `Drop ${activeConfig.label.toLowerCase()} here, or click to browse`}
          </p>
          <input
            key={activeTab}
            ref={inputRef}
            type="file"
            accept={activeConfig.accept}
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      )}

      {sources.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="font-data text-xs text-parchment-500">Loaded sources:</p>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {sources.map((source) => (
              <div
                key={source.id}
                className={`flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  activeSourceId === source.id
                    ? "bg-ember-500/10 border border-ember-500"
                    : "bg-ink-800 border border-ink-600 hover:border-ink-500"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="font-data text-xs text-parchment-400">{source.type}</span>
                  <span className="font-medium text-parchment-100 truncate">{source.name}</span>
                  <span className="font-data text-xs text-parchment-500">{source.chunks ?? 0} chunks</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setActiveSource(activeSourceId === source.id ? null : source.id)}
                    className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                      activeSourceId === source.id
                        ? "bg-ember-500 text-ink-950"
                        : "text-parchment-500 hover:text-parchment-100"
                    }`}
                  >
                    {activeSourceId === source.id ? "Active" : "Select"}
                  </button>
                  <button
                    onClick={() => handleDeleteSource(source.id)}
                    className="rounded px-2 py-1 text-xs text-parchment-500 hover:text-err-500 transition-colors"
                    title="Delete source"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Curriculum Browser */}
      {curriculumSources.length > 0 && (
        <div className="mt-6 border-t border-ink-700 pt-6">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-base text-parchment-100">Curriculum</h3>
            {curriculumActive && curriculumSource && (
              <Button variant="ghost" size="sm" onClick={handleCurriculumClear}>
                Clear curriculum
              </Button>
            )}
          </div>
          <p className="mt-1 text-xs text-parchment-500">
            Select a curriculum book to use with the tutor. Your uploaded sources remain active.
          </p>

          <div className="mt-4 space-y-3 max-h-60 overflow-y-auto">
            {grades.length === 0 ? (
              <p className="text-sm text-parchment-500">No curriculum data available.</p>
            ) : (
              grades.map((grade) => (
                <div key={grade} className="space-y-2">
                  <p className="font-data text-xs text-parchment-400">Grade {grade}</p>
                  {Object.entries(hierarchy[grade]).map(([subject, seriesMap]) => (
                    <div key={subject} className="ml-3 space-y-2 border-l border-ink-600 pl-3">
                      <p className="font-data text-xs text-parchment-500">{subject}</p>
                      {Object.entries(seriesMap).map(([series, bookMap]) => (
                        <div key={series} className="ml-3 space-y-2 border-l border-ink-600 pl-3">
                          <p className="font-data text-xs text-parchment-500">{series}</p>
                          {Object.entries(bookMap).map(([bookTitle, parts]) => (
                            <div key={bookTitle} className="ml-3 space-y-1 border-l border-ink-600 pl-3">
                              <p className="font-medium text-xs text-parchment-300">{bookTitle}</p>
{parts.map((part) => (
                                <div key={part.id} className="space-y-1">
                                  <button
                                    onClick={() => handleCurriculumSelect(part, 0)}
                                    className={`w-full text-left rounded px-2 py-1.5 text-xs font-medium transition-colors ${
                                      curriculumActive && curriculumSource?.id === part.id && curriculumChapterNumber === 0
                                        ? "bg-ember-500/10 text-ember-400 border border-ember-500"
                                        : "text-parchment-500 hover:bg-ink-800 hover:text-parchment-100"
                                  }`}
                                    >
                                      Part {part.part} {part.chapter ? `— ${part.chapter}` : ""}
                                      {part.chapter_number && <span className="font-data text-xs text-parchment-400"> (Ch {part.chapter_number})</span>}
                                    </button>
                                  {part.chapter_number && Array.from({ length: part.chapter_number }, (_, i) => i + 1).map((ch) => (
                                    <button
                                      key={ch}
                                      onClick={() => handleCurriculumSelect(part, ch)}
                                      className={`w-full text-left rounded px-2 py-1 ml-4 text-xs font-medium transition-colors ${
                                        curriculumActive && curriculumSource?.id === part.id && curriculumChapterNumber === ch
                                          ? "bg-ember-500/10 text-ember-400 border border-ember-500"
                                          : "text-parchment-500 hover:bg-ink-800 hover:text-parchment-100"
                                      }`}
                                    >
                                      <span className="ml-2">Chapter {ch}</span>
                                    </button>
                                  ))}
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <Button className="mt-5 w-full" onClick={handleUpload} loading={loading}>
        {loading ? "Forging chunks..." : "Upload & process"}
      </Button>
    </Card>
  );
}