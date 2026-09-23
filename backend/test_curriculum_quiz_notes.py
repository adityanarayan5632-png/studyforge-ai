"""M9.2A Curriculum Quiz + Notes Deterministic Tests.

Verifies curriculum retrieval isolation using unique fixture markers
and monkeypatched LLM to capture actual generator prompts.
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
import requests
from dotenv import load_dotenv
from supabase import create_client
from vector_store import collection

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SECRET_KEY"]
API_BASE = os.getenv("STUDYFORGE_API_BASE", "http://127.0.0.1:8080")

# Create Supabase admin client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_PASSWORD = "TestPass123!"


def create_test_user(email: str, grade: int = None) -> dict:
    """Create a test user via Supabase Admin API with optional grade in profile."""
    unique_email = f"{email.split('@')[0]}_{uuid.uuid4().hex[:8]}@{email.split('@')[1]}"

    response = supabase_admin.auth.admin.create_user({
        "email": unique_email,
        "password": TEST_PASSWORD,
        "email_confirm": True,
        "user_metadata": {"full_name": unique_email.split("@")[0].title()}
    })
    user = response.user

    if grade is not None:
        supabase_admin.table("profiles").insert({
            "id": user.id,
            "display_name": unique_email.split("@")[0].title(),
            "grade": grade,
            "board": "CBSE"
        }).execute()

    return {"user": user, "email": unique_email}


def sign_in_user(email: str) -> str:
    """Sign in a user and return access token."""
    response = supabase_admin.auth.sign_in_with_password({
        "email": email,
        "password": TEST_PASSWORD
    })
    return response.session.access_token


# Unique fixture markers for deterministic retrieval verification
MARKERS = {
    "SOURCE_A": {
        "grade": 1,
        "subject": "Math",
        "book_series": "MathWorld",
        "book_title": "MathWorld Grade 1 Part 1",
        "chapters": {
            1: "ALPHA_ADDITION",
            2: "ALPHA_SUBTRACTION",
            3: "ALPHA_MULTIPLICATION",
        }
    },
    "SOURCE_B": {
        "grade": 1,
        "subject": "Science",
        "book_series": "ScienceWorld",
        "book_title": "ScienceWorld Grade 1 Part 1",
        "chapters": {
            1: "BETA_PLANTS",
            2: "BETA_ANIMALS",
            3: "BETA_BODY",
        }
    },
    "SOURCE_C": {
        "grade": 5,
        "subject": "Math",
        "book_series": "MathWorld",
        "book_title": "MathWorld Grade 5 Part 1",
        "chapters": {
            1: "GAMMA_FRACTIONS",
            2: "GAMMA_DECIMALS",
            3: "GAMMA_GEOMETRY",
        }
    },
}


def _clean_chroma():
    """Remove test curriculum sources from Chroma."""
    existing = collection.get(where={"source_kind": "curriculum"})
    for meta in existing.get("metadatas", []):
        if meta.get("source_id", "").startswith("test_m92a_"):
            collection.delete(where={"source_id": meta["source_id"]})


def _ingest_fixture_chapters():
    """Create deterministic curriculum fixtures in Chroma."""
    _clean_chroma()

    source_ids = {}

    for source_key, cfg in MARKERS.items():
        source_id = f"test_m92a_{source_key.lower()}"
        source_ids[source_key] = source_id

        for ch_num, marker in cfg["chapters"].items():
            text = f"Chapter {ch_num}: {marker} content for {cfg['book_title']}."

            collection.add(
                ids=[f"{source_id}_ch{ch_num}"],
                documents=[text],
                embeddings=[[0.0] * 1024],
                metadatas=[{
                    "source_id": source_id,
                    "source_name": f"{cfg['book_title']} Ch{ch_num}",
                    "source_type": "pdf",
                    "source_kind": "curriculum",
                    "created_at": "2024-01-01T00:00:00Z",
                    "chunk_index": 0,
                    "grade": cfg["grade"],
                    "subject": cfg["subject"],
                    "language": "en",
                    "book_series": cfg["book_series"],
                    "book_title": cfg["book_title"],
                    "part": 1,
                    "is_supplement": False,
                    "chapter": f"Chapter {ch_num}",
                    "chapter_number": ch_num,
                }]
            )

    return source_ids


class TestM92ACurriculumQuizNotes:
    """M9.2A Curriculum Quiz + Notes deterministic tests."""

    # Test users
    token_grade1: str = ""
    token_grade5: str = ""
    user_grade1_id: str = ""
    user_grade5_id: str = ""

    # Deterministic curriculum source IDs
    source_a_id: str = ""
    source_b_id: str = ""
    source_c_id: str = ""

    @classmethod
    def setup_class(cls):
        print("\n=== Setting up M9.2A Deterministic Curriculum Tests ===")

        # Create deterministic Chroma fixtures
        source_ids = _ingest_fixture_chapters()
        cls.source_a_id = source_ids["SOURCE_A"]
        cls.source_b_id = source_ids["SOURCE_B"]
        cls.source_c_id = source_ids["SOURCE_C"]
        print(f"SOURCE A: {cls.source_a_id}")
        print(f"SOURCE B: {cls.source_b_id}")
        print(f"SOURCE C: {cls.source_c_id}")

        # Create test users
        user_1 = create_test_user("student_grade1_test@example.com", grade=1)
        user_5 = create_test_user("student_grade5_test@example.com", grade=5)

        cls.user_grade1_id = user_1["user"].id
        cls.user_grade5_id = user_5["user"].id

        print(f"Grade 1 user: {cls.user_grade1_id}")
        print(f"Grade 5 user: {cls.user_grade5_id}")

        print("Signing in users...")
        cls.token_grade1 = sign_in_user(user_1["email"])
        cls.token_grade5 = sign_in_user(user_5["email"])
        print("Tokens obtained")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ---- Deterministic Generator Tests ----

    def test_source_a_all_chapters_quiz(self):
        """Quiz: SOURCE A Grade 1 all chapters -> only SOURCE A markers present."""
        import quiz_generator

        captured = {}

        def fake_ask_llm(*args, **kwargs):
            captured["prompt"] = args[0] if args else kwargs.get("prompt", "")
            return "fake quiz output"

        with patch.object(quiz_generator, "ask_llm", fake_ask_llm):
            quiz_generator.generate_quiz(
                source_id=None,
                owner_user_id=self.user_grade1_id,
                use_curriculum=True,
                curriculum_source_id=self.source_a_id,
                chapter_number=None,
                grade=1,
            )

        prompt = captured["prompt"]
        print(f"Captured prompt length: {len(prompt)}")

        # All SOURCE A chapters must be present
        assert "ALPHA_ADDITION" in prompt
        assert "ALPHA_SUBTRACTION" in prompt
        assert "ALPHA_MULTIPLICATION" in prompt

        # No SOURCE B markers
        assert "BETA_PLANTS" not in prompt
        assert "BETA_ANIMALS" not in prompt
        assert "BETA_BODY" not in prompt

        # No SOURCE C markers
        assert "GAMMA_FRACTIONS" not in prompt
        assert "GAMMA_DECIMALS" not in prompt
        assert "GAMMA_GEOMETRY" not in prompt

    def test_source_a_chapter1_notes(self):
        """Notes: SOURCE A Grade 1 Chapter 1 -> only ALPHA_ADDITION present."""
        import notes_generator

        captured = {}

        def fake_ask_llm(*args, **kwargs):
            captured["prompt"] = args[0] if args else kwargs.get("prompt", "")
            return "fake notes output"

        with patch.object(notes_generator, "ask_llm", fake_ask_llm):
            notes_generator.generate_notes(
                source_id=None,
                owner_user_id=self.user_grade1_id,
                use_curriculum=True,
                curriculum_source_id=self.source_a_id,
                chapter_number=1,
                grade=1,
            )

        prompt = captured["prompt"]

        # Only Chapter 1 marker present
        assert "ALPHA_ADDITION" in prompt

        # Other SOURCE A chapters absent
        assert "ALPHA_SUBTRACTION" not in prompt
        assert "ALPHA_MULTIPLICATION" not in prompt

        # No SOURCE B markers
        assert "BETA_PLANTS" not in prompt
        assert "BETA_ANIMALS" not in prompt
        assert "BETA_BODY" not in prompt

        # No SOURCE C markers
        assert "GAMMA_FRACTIONS" not in prompt
        assert "GAMMA_DECIMALS" not in prompt
        assert "GAMMA_GEOMETRY" not in prompt

    def test_source_b_chapter1_quiz(self):
        """Quiz: SOURCE B Grade 1 Chapter 1 -> only BETA_PLANTS present."""
        import quiz_generator

        captured = {}

        def fake_ask_llm(*args, **kwargs):
            captured["prompt"] = args[0] if args else kwargs.get("prompt", "")
            return "fake quiz output"

        with patch.object(quiz_generator, "ask_llm", fake_ask_llm):
            quiz_generator.generate_quiz(
                source_id=None,
                owner_user_id=self.user_grade1_id,
                use_curriculum=True,
                curriculum_source_id=self.source_b_id,
                chapter_number=1,
                grade=1,
            )

        prompt = captured["prompt"]

        assert "BETA_PLANTS" in prompt

        # Other SOURCE B chapters absent
        assert "BETA_ANIMALS" not in prompt
        assert "BETA_BODY" not in prompt

        # No SOURCE A markers
        assert "ALPHA_ADDITION" not in prompt
        assert "ALPHA_SUBTRACTION" not in prompt
        assert "ALPHA_MULTIPLICATION" not in prompt

        # No SOURCE C markers
        assert "GAMMA_FRACTIONS" not in prompt
        assert "GAMMA_DECIMALS" not in prompt
        assert "GAMMA_GEOMETRY" not in prompt

    def test_source_a_chapter2_quiz(self):
        """Quiz: SOURCE A Grade 1 Chapter 2 -> only ALPHA_SUBTRACTION present."""
        import quiz_generator

        captured = {}

        def fake_ask_llm(*args, **kwargs):
            captured["prompt"] = args[0] if args else kwargs.get("prompt", "")
            return "fake quiz output"

        with patch.object(quiz_generator, "ask_llm", fake_ask_llm):
            quiz_generator.generate_quiz(
                source_id=None,
                owner_user_id=self.user_grade1_id,
                use_curriculum=True,
                curriculum_source_id=self.source_a_id,
                chapter_number=2,
                grade=1,
            )

        prompt = captured["prompt"]

        assert "ALPHA_SUBTRACTION" in prompt

        # Other SOURCE A chapters absent
        assert "ALPHA_ADDITION" not in prompt
        assert "ALPHA_MULTIPLICATION" not in prompt

        # No SOURCE B markers
        assert "BETA_PLANTS" not in prompt
        assert "BETA_ANIMALS" not in prompt
        assert "BETA_BODY" not in prompt

        # No SOURCE C markers
        assert "GAMMA_FRACTIONS" not in prompt
        assert "GAMMA_DECIMALS" not in prompt
        assert "GAMMA_GEOMETRY" not in prompt

    # ---- HTTP Authorization / Input Validation Tests ----

    def test_grade_authorization_blocked(self):
        """Grade 1 user + Grade 5 curriculum source -> HTTP 400."""
        r = requests.post(
            f"{API_BASE}/generate-quiz",
            json={"use_curriculum": True, "curriculum_source_id": self.source_c_id},
            headers=self._headers(self.token_grade1),
            timeout=30
        )
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower() or "not authorized" in r.json()["detail"].lower()

    def test_client_grade_manipulation_ignored(self):
        """Client-supplied grade cannot override profile grade."""
        # Grade 1 user requesting Grade 1 source with client grade=5
        # Should succeed because profile grade is 1 and source is Grade 1
        r = requests.post(
            f"{API_BASE}/generate-quiz",
            json={"use_curriculum": True, "curriculum_source_id": self.source_a_id, "grade": 5},
            headers=self._headers(self.token_grade1),
            timeout=180
        )
        assert r.status_code == 200

    def test_missing_curriculum_source_id(self):
        """use_curriculum=True without curriculum_source_id -> HTTP 400."""
        r = requests.post(
            f"{API_BASE}/generate-quiz",
            json={"use_curriculum": True},
            headers=self._headers(self.token_grade1),
            timeout=30
        )
        assert r.status_code == 400
        assert "select a curriculum book" in r.json()["detail"].lower()

    def test_nonexistent_curriculum_source_id(self):
        """Nonexistent curriculum_source_id -> HTTP 400."""
        r = requests.post(
            f"{API_BASE}/generate-quiz",
            json={"use_curriculum": True, "curriculum_source_id": "nonexistent-id-12345"},
            headers=self._headers(self.token_grade1),
            timeout=30
        )
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower() or "not authorized" in r.json()["detail"].lower()

    def test_invalid_chapter_returns_empty(self):
        """Invalid chapter -> generator returns controlled empty-content response."""
        import quiz_generator

        # Direct generator call with invalid chapter
        result = quiz_generator.generate_quiz(
            source_id=None,
            owner_user_id=self.user_grade1_id,
            use_curriculum=True,
            curriculum_source_id=self.source_a_id,
            chapter_number=99,
            grade=1,
        )
        # Generator returns its existing controlled response for no content
        assert "no curriculum content" in result.lower()

    # ---- Normal User Regression Tests ----

    def test_normal_user_quiz(self):
        """Normal user Quiz with private source -> unchanged behavior."""
        import fitz
        import tempfile

        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "My private document about quantum physics.")
        path = tempfile.mktemp(suffix=".pdf")
        pdf.save(path)
        pdf.close()

        with open(path, "rb") as f:
            r = requests.post(
                f"{API_BASE}/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=self._headers(self.token_grade1),
                timeout=30
            )
        assert r.status_code == 200
        source_id = r.json()["source_id"]

        r = requests.post(
            f"{API_BASE}/generate-quiz",
            json={"source_id": source_id},
            headers=self._headers(self.token_grade1),
            timeout=180
        )
        assert r.status_code == 200
        quiz = r.json()["quiz"]
        # Should contain quantum physics content
        assert "quantum" in quiz.lower() or "physics" in quiz.lower()

    def test_normal_user_notes(self):
        """Normal user Notes with private source -> unchanged behavior."""
        import fitz
        import tempfile

        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "My private document about quantum physics.")
        path = tempfile.mktemp(suffix=".pdf")
        pdf.save(path)
        pdf.close()

        with open(path, "rb") as f:
            r = requests.post(
                f"{API_BASE}/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=self._headers(self.token_grade1),
                timeout=30
            )
        assert r.status_code == 200
        source_id = r.json()["source_id"]

        r = requests.post(
            f"{API_BASE}/generate-notes",
            json={"source_id": source_id},
            headers=self._headers(self.token_grade1),
            timeout=60
        )
        assert r.status_code == 200
        notes = r.json()["notes"]
        assert "quantum" in notes.lower() or "physics" in notes.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])