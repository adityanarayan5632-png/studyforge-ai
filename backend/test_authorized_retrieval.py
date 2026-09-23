"""Authorized vector retrieval tests for Phase 2.5C-3A.

Tests that Chroma retrieval enforces authenticated student's source ownership.
"""

import os
import tempfile
import pytest
import requests
import fitz
import uuid
import jwt
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from vector_store import search, search_by_source
from embedder import model

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# Configuration
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SECRET_KEY"]
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

# Create Supabase admin client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_USER_A_EMAIL = "student_a_test@example.com"
TEST_USER_B_EMAIL = "student_b_test@example.com"
TEST_PASSWORD = "TestPass123!"


def create_test_user(email: str) -> dict:
    """Create a test user via Supabase Admin API."""
    # Generate unique email to avoid conflicts across test runs
    unique_email = f"{email.split('@')[0]}_{uuid.uuid4().hex[:8]}@{email.split('@')[1]}"

    # Delete if exists
    try:
        users = supabase_admin.auth.admin.list_users()
        for user in users:
            if user.email == unique_email:
                supabase_admin.auth.admin.delete_user(user.id)
    except Exception:
        pass

    response = supabase_admin.auth.admin.create_user({
        "email": unique_email,
        "password": TEST_PASSWORD,
        "email_confirm": True,
        "user_metadata": {"full_name": unique_email.split("@")[0].title()}
    })
    return response.user


def sign_in_user(email: str) -> tuple[str, str]:
    """Sign in a user and return (access_token, user_id_from_jwt)."""
    response = supabase_admin.auth.sign_in_with_password({
        "email": email,
        "password": TEST_PASSWORD
    })
    access_token = response.session.access_token
    # Decode JWT to get the actual user ID (sub claim)
    payload = jwt.decode(access_token, options={"verify_signature": False})
    user_id = payload["sub"]
    return access_token, user_id


def create_test_pdf(content: str) -> str:
    """Create a temporary PDF file with given content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    path = tempfile.mktemp(suffix=".pdf")
    doc.save(path)
    doc.close()
    return path


# Test document content - short educational sentences that survive chunking
SOURCE_A_TEXT = "Machine learning is a branch of artificial intelligence."
SOURCE_B_TEXT = "Quantum computing uses quantum bits called qubits."

# Unique phrases that should survive chunking
SOURCE_A_UNIQUE = "branch of artificial intelligence"
SOURCE_B_UNIQUE = "quantum bits called qubits"

# Source-specific content markers that exist in the document but NOT in the test questions
# These are used to verify no actual source content leakage (vs just echoing the question)
SOURCE_A_LEAK_MARKER = "machine learning is a branch"
SOURCE_B_LEAK_MARKER = "quantum computing uses"


class TestAuthorizedVectorRetrieval:
    """Authorized vector retrieval security tests."""

    source_a_id: str = ""
    source_b_id: str = ""
    token_a: str = ""
    token_b: str = ""

    @classmethod
    def setup_class(cls):
        print(f"\nCreating test users...")
        cls.user_a = create_test_user(TEST_USER_A_EMAIL)
        cls.user_b = create_test_user(TEST_USER_B_EMAIL)
        print(f"User A: {cls.user_a.id} ({cls.user_a.email})")
        print(f"User B: {cls.user_b.id} ({cls.user_b.email})")

        print("Signing in users...")
        cls.token_a, cls.user_a_id = sign_in_user(cls.user_a.email)
        cls.token_b, cls.user_b_id = sign_in_user(cls.user_b.email)
        print(f"User A authenticated as: {cls.user_a_id}")
        print(f"User B authenticated as: {cls.user_b_id}")
        print(f"Token A obtained: {cls.token_a[:20]}...")
        print(f"Token B obtained: {cls.token_b[:20]}...")

        # Upload sources
        print("Uploading sources...")
        pdf_a = create_test_pdf(SOURCE_A_TEXT)
        with open(pdf_a, "rb") as f:
            r = requests.post(f"{API_BASE}/upload", files={"file": f}, headers={"Authorization": f"Bearer {cls.token_a}"}, timeout=30)
        assert r.status_code == 200, f"A upload failed: {r.text}"
        cls.source_a_id = r.json()["source_id"]
        print(f"A uploaded source: {cls.source_a_id}")

        pdf_b = create_test_pdf(SOURCE_B_TEXT)
        with open(pdf_b, "rb") as f:
            r = requests.post(f"{API_BASE}/upload", files={"file": f}, headers={"Authorization": f"Bearer {cls.token_b}"}, timeout=30)
        assert r.status_code == 200, f"B upload failed: {r.text}"
        cls.source_b_id = r.json()["source_id"]
        print(f"B uploaded source: {cls.source_b_id}")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ── Vector-store level tests (direct Chroma access) ─────────────────

    def test_vector_global_retrieval_isolation(self):
        """1. A global retrieval retrieves A. 2. A global retrieval cannot retrieve B content.
           3. B global retrieval retrieves B. 4. B global retrieval cannot retrieve A content."""
        # A's global search for B's unique phrase → should NOT find
        results_a = search(model.encode(SOURCE_B_UNIQUE), n_results=5, owner_user_id=self.user_a_id)
        docs_a = results_a.get("documents", [[]])[0]
        metadatas_a = results_a.get("metadatas", [[]])[0]

        for meta in metadatas_a:
            assert meta.get("owner_user_id") == self.user_a_id, \
                f"Global search leaked other user's data: {meta}"
        all_text = " ".join(docs_a)
        assert SOURCE_B_UNIQUE not in all_text, "A's global search leaked B's content"
        print(f"A global search found {len(docs_a)} docs, all owned by A")

        # B's global search for A's unique phrase → should NOT find
        results_b = search(model.encode(SOURCE_A_UNIQUE), n_results=5, owner_user_id=self.user_b_id)
        docs_b = results_b.get("documents", [[]])[0]
        metadatas_b = results_b.get("metadatas", [[]])[0]

        for meta in metadatas_b:
            assert meta.get("owner_user_id") == self.user_b_id, \
                f"B's global search leaked other user's data: {meta}"
        all_text = " ".join(docs_b)
        assert SOURCE_A_UNIQUE not in all_text, "B's global search leaked A's content"
        print(f"B global search found {len(docs_b)} docs, all owned by B")

    def test_vector_scoped_retrieval_isolation(self):
        """5. A scoped retrieval retrieves A. 6. A scoped retrieval cannot retrieve B.
           7. B scoped retrieval retrieves B. 8. B scoped retrieval cannot retrieve A."""
        # A scoped to B's source → empty
        results = search_by_source(
            self.source_b_id,
            model.encode(SOURCE_B_UNIQUE),
            owner_user_id=self.user_a_id
        )
        docs = results.get("documents", [[]])[0]
        assert len(docs) == 0, "A scoped to B's source should return empty"
        print("A scoped to B: correctly returned empty")

        # B scoped to A's source → empty
        results = search_by_source(
            self.source_a_id,
            model.encode(SOURCE_A_UNIQUE),
            owner_user_id=self.user_b_id
        )
        docs = results.get("documents", [[]])[0]
        assert len(docs) == 0, "B scoped to A's source should return empty"
        print("B scoped to A: correctly returned empty")

    def test_vector_scoped_own_works(self):
        """A scoped to own source A works; B scoped to own source B works."""
        # A scoped to own source A
        results = search_by_source(
            self.source_a_id,
            model.encode(SOURCE_A_UNIQUE),
            owner_user_id=self.user_a_id
        )
        docs = results.get("documents", [[]])[0]
        assert len(docs) > 0, "A scoped to own source should return results"
        all_text = " ".join(docs)
        assert SOURCE_A_UNIQUE in all_text
        print(f"A scoped to own A: found {len(docs)} chunks")

        # B scoped to own source B
        results = search_by_source(
            self.source_b_id,
            model.encode(SOURCE_B_UNIQUE),
            owner_user_id=self.user_b_id
        )
        docs = results.get("documents", [[]])[0]
        assert len(docs) > 0, "B scoped to own source should return results"
        all_text = " ".join(docs)
        assert SOURCE_B_UNIQUE in all_text
        print(f"B scoped to own B: found {len(docs)} chunks")

    # ── API-level tests (via /ask endpoint) ─────────────────────────────

    def test_api_global_retrieval_isolation(self):
        """1. A global retrieval retrieves A. 2. A global retrieval cannot retrieve B content.
           3. B global retrieval retrieves B. 4. B global retrieval cannot retrieve A content."""
        # A asks about their unique phrase
        r = requests.post(f"{API_BASE}/ask", params={"question": "What is machine learning?"}, headers=self._headers(self.token_a), timeout=60)
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" not in answer
        assert "machine learning" in answer or "artificial intelligence" in answer
        print(f"A global ML query: {answer[:100]}...")

        # A asks about B's UNIQUE phrase (not general quantum knowledge)
        r = requests.post(f"{API_BASE}/ask", params={"question": "What does the document say about quantum bits called qubits?"}, headers=self._headers(self.token_a), timeout=60)
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        # Verify source isolation: B's source-specific content must NOT leak to A
        # (Question contains "quantum bits called qubits", so we check for "quantum computing uses" which is only in the doc)
        assert SOURCE_B_LEAK_MARKER not in answer, f"Source B content leaked to User A: {answer[:200]}"
        print(f"A global Quantum query: {answer[:100]}...")

        # B asks about their unique phrase
        r = requests.post(f"{API_BASE}/ask", params={"question": "What is quantum computing?"}, headers=self._headers(self.token_b), timeout=60)
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" not in answer
        assert "quantum" in answer or "qubit" in answer
        print(f"B global Quantum query: {answer[:100]}...")

        # B asks about A's UNIQUE phrase
        r = requests.post(f"{API_BASE}/ask", params={"question": "What does the document say about a branch of artificial intelligence?"}, headers=self._headers(self.token_b), timeout=60)
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        # Verify source isolation: A's source-specific content must NOT leak to B
        # (Question contains "branch of artificial intelligence", so we check for the full phrase which is only in the doc)
        assert SOURCE_A_LEAK_MARKER not in answer, f"Source A content leaked to User B: {answer[:200]}"
        print(f"B global ML query: {answer[:100]}...")

    def test_api_scoped_retrieval_own_source(self):
        """5. A scoped retrieval retrieves A."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is a branch of artificial intelligence?", "source_id": self.source_a_id},
            headers=self._headers(self.token_a), timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" not in answer
        assert "branch of artificial intelligence" in answer or "machine learning" in answer
        print(f"A scoped to A: {answer[:100]}...")

    def test_api_scoped_retrieval_other_source_denied(self):
        """6. A scoped retrieval cannot retrieve B."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What are quantum bits called qubits?", "source_id": self.source_b_id},
            headers=self._headers(self.token_a), timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" in answer
        print(f"A scoped to B (denied): {answer[:100]}...")

    def test_api_scoped_retrieval_own_source_b(self):
        """7. B scoped retrieval retrieves B."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What are quantum bits called qubits?", "source_id": self.source_b_id},
            headers=self._headers(self.token_b), timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" not in answer
        assert "quantum bits called qubits" in answer or "qubit" in answer
        print(f"B scoped to B: {answer[:100]}...")

    def test_api_scoped_retrieval_a_source_denied(self):
        """8. B scoped retrieval cannot retrieve A."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is a branch of artificial intelligence?", "source_id": self.source_a_id},
            headers=self._headers(self.token_b), timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "couldn't find relevant information" in answer
        print(f"B scoped to A (denied): {answer[:100]}...")

    # ── Legacy exclusion ────────────────────────────────────────────────

    def test_legacy_sources_excluded(self):
        """9. Legacy/unowned content remains inaccessible."""
        # A only sees their own sources
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_a), timeout=10)
        assert r.status_code == 200
        sources = r.json()["sources"]
        for s in sources:
            assert s.get("owner_user_id") == self.user_a_id, f"Legacy source exposed to A: {s}"
        print(f"A sees {len(sources)} sources, all owned by A")

        # B only sees their own sources
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_b), timeout=10)
        assert r.status_code == 200
        sources = r.json()["sources"]
        for s in sources:
            assert s.get("owner_user_id") == self.user_b_id, f"Legacy source exposed to B: {s}"
        print(f"B sees {len(sources)} sources, all owned by B")

        # Non-existent user vector search returns empty
        results = search(model.encode("test"), n_results=5, owner_user_id="non-existent-user-id")
        docs = results.get("documents", [[]])[0]
        assert len(docs) == 0, "Non-existent user vector search should return empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=120"])