# Changelog

## Multi-modal uploads + fixes

### Backend (`backend/`)

- `/upload` now routes by file extension instead of assuming PDF: PDF
  (unchanged, PyMuPDF), audio (`audio_processor.py`, local Whisper),
  video (`video_processor.py`, ffmpeg audio extraction + Whisper),
  screenshots (`image_processor.py`, Tesseract OCR). Unsupported
  extensions return `415` with the list of what's supported.
- New `/upload-youtube` endpoint (`youtube_processor.py`) — takes a URL,
  tries existing captions first (fast), falls back to downloading audio
  and transcribing with Whisper if none exist.
- **Bug fix in `vector_store.py`**: chunk IDs were always `chunk_0,
  chunk_1, ...`, so every upload after the first collided with existing
  IDs and was silently dropped (the exception was swallowed). IDs are now
  namespaced per upload (`{source_id}_chunk_{i}`), so multiple sources —
  across any of PDF/audio/video/image/YouTube — actually accumulate in
  the vector store instead of only the first upload ever sticking.
- All extraction paths raise a `422` if no text/speech could be pulled
  from the source (e.g. silent audio, blank image) instead of silently
  storing nothing.
- `requirements.txt` gains `openai-whisper`, `Pillow`, `pytesseract`,
  `yt-dlp`. System binaries `ffmpeg` and `tesseract-ocr` are required —
  see README.

### Frontend (`frontend/`)

- `UploadForge` now has a source-type selector (PDF / Audio / Video /
  Screenshot / YouTube link) instead of only accepting PDFs.
- `lib/api.ts`: `uploadPDF` renamed to `uploadFile` (handles any
  supported file type, backend dispatches by extension); added
  `uploadYoutubeLink`.
- `lib/types.ts`: added `SourceKind`.
- Logout now redirects to the landing page (`/`) instead of `/login`.

## Frontend redesign — "The Forge"

The frontend went from a single-page prototype (inline upload/ask/notes/quiz
with `alert()` calls) to a multi-page SaaS app. The backend (`backend/`) was
**not touched** — same four routes: `/upload`, `/ask`, `/generate-notes`,
`/generate-quiz`.

### Concept

Dark ink/charcoal UI with amber/molten accents. Fraunces (display serif) +
Manrope (body) + JetBrains Mono (data) — all self-hosted via `@fontsource`,
not `next/font/google`.

### New pages (`frontend/app/`)

- `login/page.tsx`, `signup/page.tsx`
- `dashboard/layout.tsx` — auth-guarded shell (sidebar + topbar)
- `dashboard/page.tsx` — overview: PDF upload widget + quick actions
- `dashboard/tutor/page.tsx` — AI Tutor chat, calls `/ask`
- `dashboard/notes/page.tsx` — calls `/generate-notes`
- `dashboard/study/page.tsx` — combined Quiz + Flashcards, tabbed, calls `/generate-quiz`
- `dashboard/settings/page.tsx` — account, plan switch, clear session data
- `app/page.tsx` — rewritten as the new landing page (previously the entire
  old single-page app)

### New components (`frontend/components/`)

- `layout/` — Logo, PublicNavbar, Footer
- `auth/` — AuthShell, AuthGuard
- `dashboard/` — Sidebar, Topbar, UploadForge, QuickActions
- `tutor/` — ChatThread
- `notes/` — NotesViewer (dependency-free renderer for the notes text format)
- `study/` — QuizPlayer, FlashcardDeck
- `landing/` — Hero, FeatureGrid, HowItWorks, PricingTiers, CTASection
- `ui/` — Button + LinkButton, Primitives (Card/Badge/Spinner/EmptyState/Input/Label), Toast

### New shared logic (`frontend/lib/`)

- `types.ts`, `api.ts` — centralized axios client, base URL via
  `NEXT_PUBLIC_API_URL` instead of a hardcoded `localhost` URL
- `auth-context.tsx` — the backend has no auth endpoints, so this is a real
  but self-contained client-side account system using `localStorage`.
  Isolated behind one file / the `useAuth()` hook so it can be swapped for
  real backend auth later.
- `study-context.tsx` — shares uploaded file / notes / quiz state across
  dashboard pages via `sessionStorage`
- `parseQuiz.ts` — parses the raw LLM quiz text into structured questions;
  also derives flashcards, since there's no separate flashcard endpoint
  (front = question, back = correct answer + explanation)

### Modified

- `app/layout.tsx`, `app/globals.css` (new design tokens)
- `package.json` — added `@fontsource-variable/fraunces`, `@fontsource/manrope`, `@fontsource/jetbrains-mono`
- `README.md`
- Added `.env.local.example`
