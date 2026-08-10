"use client";

import { useRef, useState } from "react";
import { Card, Badge, Input } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { uploadFile, uploadYoutubeLink } from "@/lib/api";
import { useStudy } from "@/lib/study-context";
import { useToast } from "@/components/ui/Toast";
import type { SourceKind } from "@/lib/types";

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

export function UploadForge() {
  const [activeTab, setActiveTab] = useState<SourceKind>("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { uploadedFileName, chunksCreated, setUpload } = useStudy();
  const { showToast } = useToast();

  const activeConfig = SOURCE_TABS.find((t) => t.id === activeTab)!;

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
    setLoading(true);
    try {
      if (activeTab === "youtube") {
        const trimmed = youtubeUrl.trim();
        if (!trimmed) {
          showToast("Paste a YouTube link first.", "error");
          return;
        }
        const result = await uploadYoutubeLink(trimmed);
        setUpload(trimmed, result.chunks_created);
        showToast(result.message || "YouTube video processed.", "success");
      } else {
        if (!file) {
          showToast(`Choose ${activeConfig.label === "PDF" ? "a" : "an"} ${activeConfig.label.toLowerCase()} file first.`, "error");
          return;
        }
        const result = await uploadFile(file);
        setUpload(file.name, result.chunks_created);
        showToast(result.message || "Uploaded and processed.", "success");
      }
    } catch (error) {
      console.error(error);
      showToast("Processing failed. Is the backend running?", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg text-parchment-100">Feed the forge</h2>
        {uploadedFileName && <Badge tone="ok">Material loaded</Badge>}
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

      {uploadedFileName && (
        <p className="mt-3 font-data text-xs text-parchment-500">
          Last processed: {uploadedFileName} &middot; {chunksCreated ?? 0} chunks created
        </p>
      )}

      <Button className="mt-5 w-full" onClick={handleUpload} loading={loading}>
        {loading ? "Forging chunks..." : "Upload & process"}
      </Button>
    </Card>
  );
}
