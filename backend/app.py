import logging
import os
import shutil
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from chunker import chunk_text
from embedder import create_embeddings
from notes_generator import generate_notes
from pdf_processor import extract_text_from_pdf
from quiz_generator import generate_quiz
from rag_pipeline import answer_question
from vector_store import delete_source, get_sources, store_chunks
from auth import get_current_user, SupabaseUser
from supabase import create_client, Client

# Optional heavy imports - only needed for upload features
try:
    from audio_processor import transcribe_audio as _transcribe_audio
    from image_processor import extract_text_from_image
    from video_processor import extract_text_from_video
    from youtube_processor import extract_text_from_youtube
    HEAVY_IMPORTS_AVAILABLE = True
except ImportError:
    HEAVY_IMPORTS_AVAILABLE = False
    _transcribe_audio = None
    extract_text_from_image = None
    extract_text_from_video = None
    extract_text_from_youtube = None

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SECRET_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI()

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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


@app.get("/auth/me")
async def get_current_user_info(user: SupabaseUser = Depends(get_current_user)):
    """Test endpoint to verify Supabase JWT authentication."""
    return {
        "user_id": user.sub,
        "email": user.email,
        "role": user.role,
    }


# Dashboard Summary Models
class DashboardProfile(BaseModel):
    display_name: Optional[str] = None
    grade: Optional[int] = None
    board: Optional[str] = None


class DashboardConversation(BaseModel):
    id: str
    title: str
    updated_at: str
    message_count: int
    last_message_preview: Optional[str] = None


class DashboardQuizAttempt(BaseModel):
    id: str
    title: Optional[str] = None
    score: int
    total_questions: int
    percentage: float
    created_at: str


class DashboardQuizPerformance(BaseModel):
    total_attempts: int
    average_score: float
    recent_attempts: List[DashboardQuizAttempt]


class DashboardActivity(BaseModel):
    id: str
    activity_type: str
    metadata: Optional[dict] = None
    created_at: str


class DashboardSource(BaseModel):
    id: str
    name: str
    type: str
    created_at: str


class DashboardSummary(BaseModel):
    profile: DashboardProfile
    recent_conversation: Optional[DashboardConversation] = None
    quiz_performance: DashboardQuizPerformance
    recent_activities: List[dict] = []
    recent_sources: List[dict] = []
    source_count: int


@app.get("/dashboard/summary")
async def get_dashboard_summary(user: SupabaseUser = Depends(get_current_user)):
    """Get aggregated dashboard summary for the authenticated user."""
    user_id = user.sub

    # Get profile
    profile_result = supabase.table("profiles") \
        .select("display_name, grade, board") \
        .eq("id", user_id) \
        .single() \
        .execute()

    profile_data = profile_result.data or {}
    profile = DashboardProfile(
        display_name=profile_data.get("display_name"),
        grade=profile_data.get("grade"),
        board=profile_data.get("board"),
    )

    # Get recent conversation with messages
    conversations_result = supabase.table("conversations") \
        .select("id, title, updated_at") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .limit(1) \
        .execute()

    recent_conversation = None
    if conversations_result.data:
        conv = conversations_result.data[0]
        # Get messages for this conversation
        messages_result = supabase.table("messages") \
            .select("role, content, created_at") \
            .eq("conversation_id", conv["id"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        last_message_preview = None
        if messages_result.data:
            last_msg = messages_result.data[0]
            preview = last_msg["content"]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            last_message_preview = preview

        # Count messages
        msg_count_result = supabase.table("messages") \
            .select("id", count="exact") \
            .eq("conversation_id", conv["id"]) \
            .execute()

        recent_conversation = DashboardConversation(
            id=conv["id"],
            title=conv["title"],
            updated_at=conv["updated_at"],
            message_count=msg_count_result.count or 0,
            last_message_preview=last_message_preview,
        )

    # Get quiz attempts
    quiz_attempts_result = supabase.table("quiz_attempts") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()

    quiz_attempts = quiz_attempts_result.data or []
    total_attempts = len(quiz_attempts)
    average_score = sum(a["percentage"] for a in quiz_attempts) / total_attempts if total_attempts > 0 else 0.0

    recent_attempts = [
        DashboardQuizAttempt(
            id=a["id"],
            title=a.get("title"),
            score=a["score"],
            total_questions=a["total_questions"],
            percentage=a["percentage"],
            created_at=a["created_at"],
        )
        for a in quiz_attempts[:5]
    ]

    quiz_performance = DashboardQuizPerformance(
        total_attempts=total_attempts,
        average_score=round(average_score, 1),
        recent_attempts=recent_attempts,
    )

    # Get recent study activities
    activities_result = supabase.table("study_activities") \
        .select("id, activity_type, metadata, created_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()

    recent_activities = activities_result.data or []

    # Get recent sources from ChromaDB
    chroma_sources = get_sources(owner_user_id=user_id)
    recent_sources = [
        {
            "id": src["source_id"],
            "name": src["source_name"],
            "type": src["source_type"],
            "created_at": src["created_at"],
        }
        for src in chroma_sources[:5]
    ]
    source_count = len(chroma_sources)

    return DashboardSummary(
        profile=profile,
        recent_conversation=recent_conversation,
        quiz_performance=quiz_performance,
        recent_activities=recent_activities,
        recent_sources=recent_sources,
        source_count=source_count,
    )


def _store_extracted_text(
    text: str, source_name: str, source_type: str, owner_user_id: str
) -> dict:
    text = (text or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail=f"Couldn't extract any text from {source_name} — it may be empty, "
            "silent, or unreadable.",
        )
    chunks = chunk_text(text)
    embeddings = create_embeddings(chunks)
    source_id = store_chunks(
        chunks, embeddings, source_name=source_name, source_type=source_type, owner_user_id=owner_user_id
    )
    return {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_type,
        "chunks_created": len(chunks),
        "message": f"{source_name} processed successfully",
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user: SupabaseUser = Depends(get_current_user)):
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
            source_type = "pdf"
        elif ext in AUDIO_EXTENSIONS:
            if not HEAVY_IMPORTS_AVAILABLE or _transcribe_audio is None:
                raise HTTPException(status_code=501, detail="Audio upload not available in this deployment")
            text = _transcribe_audio(upload_path)
            source_type = "audio"
        elif ext in VIDEO_EXTENSIONS:
            if not HEAVY_IMPORTS_AVAILABLE or extract_text_from_video is None:
                raise HTTPException(status_code=501, detail="Video upload not available in this deployment")
            text = extract_text_from_video(upload_path)
            source_type = "video"
        else:  # IMAGE_EXTENSIONS
            if not HEAVY_IMPORTS_AVAILABLE or extract_text_from_image is None:
                raise HTTPException(status_code=501, detail="Image upload not available in this deployment")
            text = extract_text_from_image(upload_path)
            source_type = "image"

        result = _store_extracted_text(text, filename, source_type, user.sub)

        # Log source uploaded activity
        supabase.table("study_activities").insert({
            "user_id": user.sub,
            "activity_type": "source_uploaded",
            "metadata": {"source_id": result["source_id"], "source_type": source_type},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

        return result
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


class YoutubeUploadRequest(BaseModel):
    url: str


@app.post("/upload-youtube")
def upload_youtube(payload: YoutubeUploadRequest, user: SupabaseUser = Depends(get_current_user)):
    """
    Ingests a YouTube video by URL. Tries existing captions first (fast),
    falling back to downloading the audio track and transcribing it with
    Whisper if no captions are available.
    """
    if not HEAVY_IMPORTS_AVAILABLE or extract_text_from_youtube is None:
        raise HTTPException(status_code=501, detail="YouTube upload not available in this deployment")
    try:
        text = extract_text_from_youtube(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Couldn't process that YouTube link: {exc}",
        )

    result = _store_extracted_text(text, payload.url, "youtube", user.sub)

    # Log source uploaded activity
    supabase.table("study_activities").insert({
        "user_id": user.sub,
        "activity_type": "source_uploaded",
        "metadata": {"source_id": result["source_id"], "source_type": "youtube"},
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    return result


class CurriculumIngestRequest(BaseModel):
    pdf_path: str
    grade: int
    subject: str
    language: str
    book_series: str
    book_title: str
    part: int
    is_supplement: bool = False


@app.post("/admin/ingest-curriculum")
def ingest_curriculum(payload: CurriculumIngestRequest, user: SupabaseUser = Depends(get_current_user)):
    ocr_lang = "hin+eng" if payload.language == "hi" else "eng"
    text = extract_text_from_pdf(payload.pdf_path, ocr_lang=ocr_lang)
    chunks = chunk_text(text)
    embeddings = create_embeddings(chunks)
    source_id = store_chunks(
        chunks,
        embeddings,
        source_name=payload.pdf_path,
        source_type="pdf",
        owner_user_id=None,
        source_kind="curriculum",
        grade=payload.grade,
        subject=payload.subject,
        language=payload.language,
        book_series=payload.book_series,
        book_title=payload.book_title,
        part=payload.part,
        is_supplement=payload.is_supplement,
    )
    return {
        "source_id": source_id,
        "chunks_created": len(chunks),
        "message": "Curriculum PDF ingested successfully",
    }


@app.get("/sources")
def list_sources(user: SupabaseUser = Depends(get_current_user)):
    user_sources = get_sources(owner_user_id=user.sub)
    curriculum_sources = get_sources(source_kind="curriculum")
    return {
        "sources": user_sources,
        "curriculum_sources": curriculum_sources,
    }


@app.delete("/sources/{source_id}")
def delete_source_endpoint(source_id: str, user: SupabaseUser = Depends(get_current_user)):
    try:
        sources = get_sources(owner_user_id=user.sub)
        if not any(s["source_id"] == source_id for s in sources):
            raise HTTPException(status_code=404, detail="Source not found")
        delete_source(source_id, owner_user_id=user.sub)

        # Log source deleted activity
        supabase.table("study_activities").insert({
            "user_id": user.sub,
            "activity_type": "source_deleted",
            "metadata": {"source_id": source_id},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

        return {"message": "Source deleted", "source_id": source_id}
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to delete source %s for user %s", source_id, user.sub)
        raise HTTPException(status_code=500, detail="Failed to delete source")


@app.post("/ask")
def ask_question(
    question: str = Query(...),
    source_id: Optional[str] = Query(None),
    use_curriculum: bool = Query(False),
    grade: Optional[int] = Query(None),
    curriculum_source_id: Optional[str] = Query(None),
    chapter_number: Optional[int] = Query(None),
    user: SupabaseUser = Depends(get_current_user),
):
    if use_curriculum:
        # Curriculum access is authorized by the student's server-side profile grade.
        try:
            profile_result = (
                supabase.table("profiles")
                .select("grade")
                .eq("id", user.sub)
                .single()
                .execute()
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="User profile not found. Please complete onboarding to access curriculum.",
            )

        profile_data = profile_result.data
        if not profile_data:
            raise HTTPException(
                status_code=400,
                detail="User profile not found. Please complete onboarding to access curriculum.",
            )

        profile_grade = profile_data.get("grade")
        if (
            profile_grade is None
            or not isinstance(profile_grade, int)
            or profile_grade < 1
            or profile_grade > 5
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid profile grade. Please complete onboarding to access curriculum.",
            )

        effective_grade = profile_grade

        if not curriculum_source_id:
            raise HTTPException(
                status_code=400,
                detail="Select a curriculum book before asking.",
            )

        # Authorize the requested curriculum source against Chroma metadata.
        curriculum_sources = get_sources(source_kind="curriculum")
        matching_sources = [
            source
            for source in curriculum_sources
            if source.get("source_id") == curriculum_source_id
            and source.get("grade") == effective_grade
        ]
        if not matching_sources:
            raise HTTPException(
                status_code=400,
                detail="Curriculum source not found or not authorized for your grade.",
            )

        answer = answer_question(
            question,
            source_id,
            owner_user_id=user.sub,
            use_curriculum=True,
            grade=effective_grade,
            source_kind="curriculum",
            curriculum_source_id=curriculum_source_id,
            chapter_number=chapter_number,
        )
    else:
        answer = answer_question(question, source_id, owner_user_id=user.sub)

    # Log tutor question activity
    supabase.table("study_activities").insert({
        "user_id": user.sub,
        "activity_type": "tutor_question",
        "metadata": {"source_id": source_id, "use_curriculum": use_curriculum},
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    return {
        "question": question,
        "answer": answer,
    }


class GenerateRequest(BaseModel):
    source_id: Optional[str] = None
    use_curriculum: bool = False
    curriculum_source_id: Optional[str] = None
    chapter_number: Optional[int] = None


@app.post("/generate-notes")
def generate_study_notes(
    payload: GenerateRequest = GenerateRequest(),
    user: SupabaseUser = Depends(get_current_user),
):
    if payload.use_curriculum:
        # Curriculum access is authorized by the student's server-side profile grade.
        profile_result = (
            supabase.table("profiles")
            .select("grade")
            .eq("id", user.sub)
            .single()
            .execute()
        )
        profile_data = profile_result.data
        if not profile_data:
            raise HTTPException(
                status_code=400,
                detail="User profile not found. Please complete onboarding.",
            )

        profile_grade = profile_data.get("grade")
        if (
            profile_grade is None
            or not isinstance(profile_grade, int)
            or profile_grade < 1
            or profile_grade > 5
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid profile grade. Please complete onboarding.",
            )

        effective_grade = profile_grade

        if not payload.curriculum_source_id:
            raise HTTPException(
                status_code=400,
                detail="Select a curriculum book before generating.",
            )

        # Authorize the requested curriculum source against Chroma metadata.
        curriculum_sources = get_sources(source_kind="curriculum")
        matching_sources = [
            source
            for source in curriculum_sources
            if source.get("source_id") == payload.curriculum_source_id
            and source.get("grade") == effective_grade
        ]
        if not matching_sources:
            raise HTTPException(
                status_code=400,
                detail="Curriculum source not found or not authorized for your grade.",
            )

        notes = generate_notes(
            source_id=None,
            owner_user_id=user.sub,
            use_curriculum=True,
            curriculum_source_id=payload.curriculum_source_id,
            chapter_number=payload.chapter_number,
            grade=effective_grade,
        )
    else:
        notes = generate_notes(payload.source_id, owner_user_id=user.sub)

    # Log notes generated activity
    supabase.table("study_activities").insert({
        "user_id": user.sub,
        "activity_type": "notes_generated",
        "metadata": {
            "source_id": payload.source_id,
            "use_curriculum": payload.use_curriculum,
        },
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    return {
        "notes": notes,
    }


@app.post("/generate-quiz")
def generate_study_quiz(
    payload: GenerateRequest = GenerateRequest(),
    user: SupabaseUser = Depends(get_current_user),
):
    if payload.use_curriculum:
        # Curriculum access is authorized by the student's server-side profile grade.
        profile_result = (
            supabase.table("profiles")
            .select("grade")
            .eq("id", user.sub)
            .single()
            .execute()
        )
        profile_data = profile_result.data
        if not profile_data:
            raise HTTPException(
                status_code=400,
                detail="User profile not found. Please complete onboarding.",
            )

        profile_grade = profile_data.get("grade")
        if (
            profile_grade is None
            or not isinstance(profile_grade, int)
            or profile_grade < 1
            or profile_grade > 5
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid profile grade. Please complete onboarding.",
            )

        effective_grade = profile_grade

        if not payload.curriculum_source_id:
            raise HTTPException(
                status_code=400,
                detail="Select a curriculum book before generating.",
            )

        # Authorize the requested curriculum source against Chroma metadata.
        curriculum_sources = get_sources(source_kind="curriculum")
        matching_sources = [
            source
            for source in curriculum_sources
            if source.get("source_id") == payload.curriculum_source_id
            and source.get("grade") == effective_grade
        ]
        if not matching_sources:
            raise HTTPException(
                status_code=400,
                detail="Curriculum source not found or not authorized for your grade.",
            )

        quiz = generate_quiz(
            source_id=None,
            owner_user_id=user.sub,
            use_curriculum=True,
            curriculum_source_id=payload.curriculum_source_id,
            chapter_number=payload.chapter_number,
            grade=effective_grade,
        )
    else:
        quiz = generate_quiz(payload.source_id, owner_user_id=user.sub)

    # Log quiz generated activity
    supabase.table("study_activities").insert({
        "user_id": user.sub,
        "activity_type": "quiz_generated",
        "metadata": {
            "source_id": payload.source_id,
            "use_curriculum": payload.use_curriculum,
        },
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    return {
        "quiz": quiz,
    }


# Quiz Attempt Models
class QuizAttemptCreate(BaseModel):
    source_id: Optional[str] = None
    title: Optional[str] = None
    score: int
    total_questions: int
    percentage: float


class QuizAttemptResponse(BaseModel):
    id: str
    user_id: str
    source_id: Optional[str] = None
    title: Optional[str] = None
    score: int
    total_questions: int
    percentage: float
    created_at: str


# Quiz Attempt Endpoints
@app.post("/quiz-attempts")
async def create_quiz_attempt(payload: QuizAttemptCreate, user: SupabaseUser = Depends(get_current_user)):
    """Save a completed quiz attempt for the authenticated user."""
    attempt_data = {
        "user_id": user.sub,
        "source_id": payload.source_id,
        "title": payload.title,
        "score": payload.score,
        "total_questions": payload.total_questions,
        "percentage": payload.percentage,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("quiz_attempts").insert(attempt_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create quiz attempt")

    # Log quiz completed activity
    supabase.table("study_activities").insert({
        "user_id": user.sub,
        "activity_type": "quiz_completed",
        "metadata": {
            "source_id": payload.source_id,
            "score": payload.score,
            "total_questions": payload.total_questions,
            "percentage": payload.percentage,
        },
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    return result.data[0]


@app.get("/quiz-attempts")
async def list_quiz_attempts(user: SupabaseUser = Depends(get_current_user)):
    """List all quiz attempts for the authenticated user."""
    result = supabase.table("quiz_attempts") \
        .select("*") \
        .eq("user_id", user.sub) \
        .order("created_at", desc=True) \
        .execute()
    return {"quiz_attempts": result.data}


@app.get("/quiz-attempts/{attempt_id}")
async def get_quiz_attempt(attempt_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Get a specific quiz attempt."""
    result = supabase.table("quiz_attempts") \
        .select("*") \
        .eq("id", attempt_id) \
        .eq("user_id", user.sub) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    return result.data


# Study Activity Models
class StudyActivityType(str, Enum):
    tutor_question = "tutor_question"
    notes_generated = "notes_generated"
    quiz_completed = "quiz_completed"
    source_uploaded = "source_uploaded"
    source_deleted = "source_deleted"


class StudyActivityCreate(BaseModel):
    activity_type: StudyActivityType
    metadata: Optional[dict] = None


class StudyActivityResponse(BaseModel):
    id: str
    user_id: str
    activity_type: str
    metadata: Optional[dict] = None
    created_at: str


class StudyActivityListResponse(BaseModel):
    activities: List[StudyActivityResponse]


# Study Activity Endpoints
@app.post("/study-activities")
async def create_study_activity(payload: StudyActivityCreate, user: SupabaseUser = Depends(get_current_user)):
    """Log a study activity for the authenticated user."""
    activity_data = {
        "user_id": user.sub,
        "activity_type": payload.activity_type.value,
        "metadata": payload.metadata,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("study_activities").insert(activity_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create study activity")
    return result.data[0]


@app.get("/study-activities")
async def list_study_activities(user: SupabaseUser = Depends(get_current_user)):
    """List all study activities for the authenticated user."""
    result = supabase.table("study_activities") \
        .select("*") \
        .eq("user_id", user.sub) \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()
    return {"activities": result.data}


# Quiz Attempt Models
class QuizAttemptCreate(BaseModel):
    source_id: Optional[str] = None
    title: Optional[str] = None
    score: int
    total_questions: int
    percentage: float


class QuizAttemptResponse(BaseModel):
    id: str
    user_id: str
    source_id: Optional[str] = None
    title: Optional[str] = None
    score: int
    total_questions: int
    percentage: float
    created_at: str


# Quiz Attempt Endpoints
@app.post("/quiz-attempts")
async def create_quiz_attempt(payload: QuizAttemptCreate, user: SupabaseUser = Depends(get_current_user)):
    """Save a completed quiz attempt for the authenticated user."""
    attempt_data = {
        "user_id": user.sub,
        "source_id": payload.source_id,
        "title": payload.title,
        "score": payload.score,
        "total_questions": payload.total_questions,
        "percentage": payload.percentage,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("quiz_attempts").insert(attempt_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create quiz attempt")
    return result.data[0]


@app.get("/quiz-attempts")
async def list_quiz_attempts(user: SupabaseUser = Depends(get_current_user)):
    """List all quiz attempts for the authenticated user."""
    result = supabase.table("quiz_attempts") \
        .select("*") \
        .eq("user_id", user.sub) \
        .order("created_at", desc=True) \
        .execute()
    return {"quiz_attempts": result.data}


@app.get("/quiz-attempts/{attempt_id}")
async def get_quiz_attempt(attempt_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Get a specific quiz attempt."""
    result = supabase.table("quiz_attempts") \
        .select("*") \
        .eq("id", attempt_id) \
        .eq("user_id", user.sub) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    return result.data


# Conversation and Message Models
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class MessageCreate(BaseModel):
    role: str  # "user" or "assistant"
    content: str


# Conversation Endpoints
@app.post("/conversations")
async def create_conversation(payload: ConversationCreate, user: SupabaseUser = Depends(get_current_user)):
    """Create a new conversation for the authenticated user."""
    conversation_data = {
        "user_id": user.sub,
        "title": payload.title or "New Conversation",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("conversations").insert(conversation_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    return result.data[0]


@app.get("/conversations")
async def list_conversations(user: SupabaseUser = Depends(get_current_user)):
    """List all conversations for the authenticated user."""
    result = supabase.table("conversations") \
        .select("*") \
        .eq("user_id", user.sub) \
        .order("updated_at", desc=True) \
        .execute()
    return {"conversations": result.data}


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Get a specific conversation with its messages."""
    # Get conversation
    conv_result = supabase.table("conversations") \
        .select("*") \
        .eq("id", conversation_id) \
        .eq("user_id", user.sub) \
        .single() \
        .execute()

    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    msg_result = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .order("created_at", desc=False) \
        .execute()

    return {
        "conversation": conv_result.data,
        "messages": msg_result.data
    }


@app.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: SupabaseUser = Depends(get_current_user)
):
    """Update conversation title."""
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    if payload.title is not None:
        update_data["title"] = payload.title

    result = supabase.table("conversations") \
        .update(update_data) \
        .eq("id", conversation_id) \
        .eq("user_id", user.sub) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    result = supabase.table("conversations") \
        .delete() \
        .eq("id", conversation_id) \
        .eq("user_id", user.sub) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted", "conversation_id": conversation_id}


# Message Endpoints
class MessageCreate(BaseModel):
    role: str  # "user" or "assistant"
    content: str


@app.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    user: SupabaseUser = Depends(get_current_user)
):
    """Add a message to a conversation."""
    # Verify conversation belongs to user
    conv_result = supabase.table("conversations") \
        .select("id") \
        .eq("id", conversation_id) \
        .eq("user_id", user.sub) \
        .single() \
        .execute()

    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_data = {
        "conversation_id": conversation_id,
        "user_id": user.sub,
        "role": payload.role,
        "content": payload.content,
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("messages").insert(message_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create message")

    # Update conversation updated_at
    supabase.table("conversations") \
        .update({"updated_at": datetime.utcnow().isoformat()}) \
        .eq("id", conversation_id) \
        .execute()

    return result.data[0]


@app.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, user: SupabaseUser = Depends(get_current_user)):
    """Get all messages for a conversation."""
    # Verify conversation belongs to user
    conv_result = supabase.table("conversations") \
        .select("id") \
        .eq("id", conversation_id) \
        .eq("user_id", user.sub) \
        .single() \
        .execute()

    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .order("created_at", desc=False) \
        .execute()

    return {"messages": msg_result.data}
