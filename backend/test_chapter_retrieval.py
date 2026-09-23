"""M9.1 Chapter-scoped curriculum retrieval tests.

Tests that curriculum retrieval correctly scopes to selected book and chapter.
"""

import os
import pytest
import requests
import fitz
import tempfile
import uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from embedder import model
from chunker import chunk_text
from embedder import create_embeddings
from vector_store import store_chunks, search, get_sources

# Load environment from backend/.env
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# Configuration - no hardcoded fallbacks
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SECRET_KEY"]
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8080")

# Create Supabase admin client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_PASSWORD = "TestPass123!"


def create_test_user(email: str, grade: int = None) -> dict:
    """Create a test user via Supabase Admin API with optional grade in profile."""
    # Generate unique email to avoid conflicts
    import uuid
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


def create_test_pdf(content: str) -> str:
    """Create a temporary PDF file with given content."""
    doc = fitz.open()
    page = doc.new_page()
    # Use a text box that wraps text automatically
    rect = fitz.Rect(72, 72, page.rect.width - 72, page.rect.height - 72)
    page.insert_textbox(rect, content, fontsize=11)
    path = tempfile.mktemp(suffix=".pdf")
    doc.save(path)
    doc.close()
    return path


def ingest_curriculum_pdf(
    pdf_path: str,
    grade: int,
    subject: str,
    language: str,
    book_series: str,
    book_title: str,
    part: int,
    is_supplement: bool = False,
) -> str:
    """Ingest a curriculum PDF and return source_id."""
    from pdf_processor import extract_text_from_pdf, detect_chapters
    from chunker import chunk_text, chunk_text_with_positions
    from embedder import create_embeddings
    from vector_store import store_chunks

    ocr_lang = "hin+eng" if language == "hi" else "eng"
    text = extract_text_from_pdf(pdf_path, ocr_lang=ocr_lang)
    chapters = detect_chapters(text)

    # Use the new position-aware chunking to get per-chunk chapter metadata
    chunk_data = chunk_text_with_positions(text)
    chunks = [c[0] for c in chunk_data]
    positions = [c[1] for c in chunk_data]
    embeddings = create_embeddings(chunks)

    # Assign chapter to each chunk based on position
    chapter_assignments = []
    for pos in positions:
        assigned_chapter = None
        assigned_number = None
        for ch in chapters:
            if ch["start_pos"] <= pos:
                assigned_chapter = ch["title"]
                assigned_number = ch["number"]
            else:
                break
        chapter_assignments.append((assigned_chapter, assigned_number))

    filename = os.path.basename(pdf_path)
    chapter_list = [ca[0] for ca in chapter_assignments]
    chapter_number_list = [ca[1] for ca in chapter_assignments]

    source_id = store_chunks(
        chunks,
        embeddings,
        source_name=filename,
        source_type="pdf",
        owner_user_id=None,
        source_kind="curriculum",
        grade=grade,
        subject=subject,
        language=language,
        book_series=book_series,
        book_title=book_title,
        part=part,
        is_supplement=is_supplement,
        chapter=chapter_list,
        chapter_number=chapter_number_list,
    )
    return source_id


def sign_in_user(email: str) -> str:
    """Sign in a user and return access token."""
    response = supabase_admin.auth.sign_in_with_password({
        "email": email,
        "password": TEST_PASSWORD
    })
    return response.session.access_token


class TestM91ChapterRetrieval:
    """M9.1 Chapter-scoped curriculum retrieval tests."""

    # Test users
    token_grade1_bookA: str = ""
    token_grade1_bookB: str = ""
    token_grade5_bookA: str = ""
    user_grade1_bookA_id: str = ""
    user_grade1_bookB_id: str = ""
    user_grade5_bookA_id: str = ""

    # Test curriculum sources (ingested once)
    source_a_id: str = ""  # Book A, Grade 1
    source_b_id: str = ""  # Book B, Grade 1
    source_c_id: str = ""  # Book A, Grade 5

    @classmethod
    def setup_class(cls):
        print(f"\n=== Setting up M9.1 Chapter Retrieval Tests ===")

        # Create test users with different grades and books
        user_a = create_test_user("student_grade1_bookA_test@example.com", grade=1)
        user_b = create_test_user("student_grade1_bookB_test@example.com", grade=1)
        user_c = create_test_user("student_grade5_bookA_test@example.com", grade=5)

        cls.user_grade1_bookA_id = user_a["user"].id
        cls.user_grade1_bookB_id = user_b["user"].id
        cls.user_grade5_bookA_id = user_c["user"].id

        cls.user_grade1_bookA_email = user_a["email"]
        cls.user_grade1_bookB_email = user_b["email"]
        cls.user_grade5_bookA_email = user_c["email"]

        print(f"Grade 1 Book A user: {cls.user_grade1_bookA_id}")
        print(f"Grade 1 Book B user: {cls.user_grade1_bookB_id}")
        print(f"Grade 5 Book A user: {cls.user_grade5_bookA_id}")

        print("Signing in users...")
        cls.token_grade1_bookA = sign_in_user(user_a["email"])
        cls.token_grade1_bookB = sign_in_user(user_b["email"])
        cls.token_grade5_bookA = sign_in_user(user_c["email"])
        print("Tokens obtained")

# Ingest curriculum sources
        # Book A Grade 1 - multiple chapters
        pdf_a1 = create_test_pdf(
            "Chapter 1: Addition basics. " + "Addition is the process of combining two or more numbers to find their total. " * 15 +
            "Chapter 2: Subtraction basics. " + "Subtraction is the process of taking one number away from another. " * 15 +
            "Chapter 3: Multiplication basics. " + "Multiplication is repeated addition of the same number. " * 15
        )
        cls.source_a_id = ingest_curriculum_pdf(
            pdf_a1, grade=1, subject="Math", language="en",
            book_series="MathWorld", book_title="MathWorld Grade 1 Part 1",
            part=1, is_supplement=False
        )
        print(f"Ingested Book A Grade 1: {cls.source_a_id}")

        # Book B Grade 1 - multiple chapters
        pdf_b1 = create_test_pdf(
            "Chapter 1: Plants. " + "Plants are living organisms that grow in soil and need sunlight and water. " * 15 +
            "Chapter 2: Animals. " + "Animals are living organisms that can move and consume other organisms for food. " * 15 +
            "Chapter 3: Human body. " + "The human body has many parts like the heart, lungs, and brain that work together. " * 15
        )
        cls.source_b_id = ingest_curriculum_pdf(
            pdf_b1, grade=1, subject="Science", language="en",
            book_series="ScienceWorld", book_title="ScienceWorld Grade 1 Part 1",
            part=1, is_supplement=False
        )
        print(f"Ingested Book B Grade 1: {cls.source_b_id}")

        # Book A Grade 5 - different grade
        pdf_a5 = create_test_pdf(
            "Chapter 1: Fractions. " + "Fractions represent parts of a whole using a numerator and denominator. " * 15 +
            "Chapter 2: Decimals. " + "Decimals are another way to write fractions using a decimal point. " * 15 +
            "Chapter 3: Geometry. " + "Geometry is the study of shapes, sizes, and positions of figures. " * 15
        )
        cls.source_c_id = ingest_curriculum_pdf(
            pdf_a5, grade=5, subject="Math", language="en",
            book_series="MathWorld", book_title="MathWorld Grade 5 Part 1",
            part=1, is_supplement=False
        )
        print(f"Ingested Book A Grade 5: {cls.source_c_id}")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_bookA_no_chapter_returns_bookA_chunks(self):
        """1. Book A + no chapter -> only Book A curriculum chunks"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the book?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        print(f"Book A no chapter: {answer[:200]}")
        assert "addition" in answer or "subtraction" in answer or "multiplication" in answer

    def test_bookA_chapter1_returns_chapter1_only(self):
        """2. Book A + Chapter 1 -> only Chapter 1 content"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in Chapter 1?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id, "chapter_number": 1},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        print(f"Book A Chapter 1: {answer[:200]}")
        assert "addition" in answer

    def test_bookA_chapter2_returns_chapter2_only(self):
        """3. Book A + Chapter 2 -> only Chapter 2 content"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in Chapter 2?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id, "chapter_number": 2},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        print("STATUS:", r.status_code)
        print("BODY:", r.text)
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        print(f"Book A Chapter 2: {answer[:200]}")
        assert "subtraction" in answer

    def test_bookA_ch1_vs_bookB_ch1_isolation(self):
        """4. Book A Chapter 1 != Book B Chapter 1 isolation"""
        # Query Book A Chapter 1
        r_a = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in this chapter?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id, "chapter_number": 1},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        assert r_a.status_code == 200
        answer_a = r_a.json()["answer"].lower()

        # Query Book B Chapter 1
        r_b = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in this chapter?", "use_curriculum": "true", "curriculum_source_id": self.source_b_id, "chapter_number": 1},
            headers=self._headers(self.token_grade1_bookB),
            timeout=60
        )
        assert r_b.status_code == 200
        answer_b = r_b.json()["answer"].lower()

        print(f"Book A Ch1: {answer_a[:100]}")
        print(f"Book B Ch1: {answer_b[:100]}")

        # Book A Ch1 should have math content, Book B Ch1 should have science content
        assert "addition" in answer_a or "subtraction" in answer_a or "multiplication" in answer_a
        assert "plant" in answer_b or "animal" in answer_b or "body" in answer_b

        # They should be different
        assert answer_a != answer_b

    def test_nonexistent_chapter_returns_no_unrelated(self):
        """5. Nonexistent chapter must not return unrelated curriculum"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in Chapter 99?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id, "chapter_number": 99},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        print(f"Nonexistent chapter: {answer[:200]}")
        # Assert that no known content markers from valid chapters are present
        book_a_markers = ["addition", "subtraction", "multiplication"]
        book_b_markers = ["plants", "animals", "body"]
        for marker in book_a_markers + book_b_markers:
            assert marker not in answer, f"Unexpected marker '{marker}' found in response for nonexistent chapter"

    def test_no_book_no_chapter_requires_explicit_source(self):
        """6. Curriculum request without curriculum_source_id should fail"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true"},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        # Current contract requires explicit curriculum_source_id
        assert r.status_code == 400
        assert "curriculum_source_id" in r.json().get("detail", "").lower() or "select a curriculum book" in r.json().get("detail", "").lower()

    def test_grade5_user_cannot_access_grade1_curriculum_via_chapter(self):
        """7. M8 profile-grade authorization remains enforced with chapter filter"""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in Chapter 1?", "use_curriculum": "true", "curriculum_source_id": self.source_a_id, "chapter_number": 1},
            headers=self._headers(self.token_grade5_bookA),
            timeout=60
        )
        # Grade 5 user trying to access Grade 1 curriculum should be forbidden
        assert r.status_code == 400
        assert "not authorized" in r.json().get("detail", "").lower() or "not found" in r.json().get("detail", "").lower() or "not authorized" in r.json().get("detail", "").lower()

    def test_normal_user_retrieval_unaffected(self):
        """8. Normal private-user retrieval remains unchanged"""
        pdf = create_test_pdf("My private document about quantum physics.")
        with open(pdf, "rb") as f:
            r = requests.post(
                f"{API_BASE}/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=self._headers(self.token_grade1_bookA),
                timeout=30
            )
        assert r.status_code == 200
        source_id = r.json()["source_id"]

        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is quantum physics?", "source_id": source_id},
            headers=self._headers(self.token_grade1_bookA),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "quantum" in answer


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=180"])