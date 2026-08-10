import os
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from audio_processor import transcribe_audio
from chunker import chunk_text
from embedder import create_embeddings
from image_processor import extract_text_from_image
from notes_generator import generate_notes
from pdf_processor import extract_text_from_pdf
from quiz_generator import generate_quiz
from rag_pipeline import answer_question
from vector_store import store_chunks
from video_processor import extract_text_from_video
from youtube_processor import extract_text_from_youtube

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PDF_EXTENSIONS = {".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


@app.get("/")
def home():
    return {"message": "StudyForge AI Backend Running"}


def _store_extracted_text(text: str, source_label: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail=f"Couldn't extract any text from {source_label} — it may be empty, "
            "silent, or unreadable.",
        )
    chunks = chunk_text(text)
    embeddings = create_embeddings(chunks)
    store_chunks(chunks, embeddings, source_id=uuid.uuid4().hex)
    return {
        "message": f"{source_label} processed successfully",
        "chunks_created": len(chunks),
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts a PDF, audio file, video file, or image (screenshot) and routes
    it to the right extractor based on file extension. Downstream chunking,
    embedding, and storage is identical regardless of source type.
    """
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext or 'unknown'}'. Supported: "
                "PDF, audio (mp3/wav/m4a/ogg/flac/aac), "
                "video (mp4/mov/avi/mkv/webm), images (png/jpg/jpeg/webp)."
            ),
        )

    upload_path = os.path.join(UPLOAD_DIR, filename)
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if ext in PDF_EXTENSIONS:
            text = extract_text_from_pdf(upload_path)
        elif ext in AUDIO_EXTENSIONS:
            text = transcribe_audio(upload_path)
        elif ext in VIDEO_EXTENSIONS:
            text = extract_text_from_video(upload_path)
        else:  # IMAGE_EXTENSIONS
            text = extract_text_from_image(upload_path)

        return _store_extracted_text(text, filename)
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


class YoutubeUploadRequest(BaseModel):
    url: str


@app.post("/upload-youtube")
def upload_youtube(payload: YoutubeUploadRequest):
    """
    Ingests a YouTube video by URL. Tries existing captions first (fast),
    falling back to downloading the audio track and transcribing it with
    Whisper if no captions are available.
    """
    try:
        text = extract_text_from_youtube(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Couldn't process that YouTube link: {exc}",
        )

    return _store_extracted_text(text, payload.url)


@app.post("/ask")
def ask_question(question: str):
    answer = answer_question(question)
    return {
        "question": question,
        "answer": answer,
    }


@app.post("/generate-notes")
def generate_study_notes():
    notes = generate_notes()
    return {
        "notes": notes,
    }


@app.post("/generate-quiz")
def generate_study_quiz():
    quiz = generate_quiz()
    return {
        "quiz": quiz,
    }
