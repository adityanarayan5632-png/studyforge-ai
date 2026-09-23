"""Regression tests for Phase 1-2 API contract - updated for authenticated endpoints."""

import os
import pytest
import requests
import fitz
import uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# Configuration
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SECRET_KEY"]
BASE = os.getenv("API_BASE", "http://127.0.0.1:8002")

# Create Supabase admin client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_EMAIL = "regression_test@example.com"
TEST_PASSWORD = "TestPass123!"


def setup_regression_user():
    """Create and sign in a regression test user."""
    # Generate unique email to avoid conflicts across test runs
    unique_email = f"{TEST_EMAIL.split('@')[0]}_{uuid.uuid4().hex[:8]}@{TEST_EMAIL.split('@')[1]}"

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
        "user_metadata": {"full_name": "Regression Test"}
    })
    user = response.user

    sign_in = supabase_admin.auth.sign_in_with_password({
        "email": unique_email,
        "password": TEST_PASSWORD
    })
    return sign_in.session.access_token, user.id


@pytest.fixture(scope="session")
def api_client():
    """HTTP client for API requests with authentication."""
    session = requests.Session()
    token, user_id = setup_regression_user()
    session.headers.update({"Authorization": f"Bearer {token}"})
    yield session
    session.close()


@pytest.fixture
def pdf_doc_a(tmp_path):
    """Create a test PDF with known content about machine learning."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Machine learning is a subset of artificial intelligence.")
    path = tmp_path / "doc_a.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def pdf_doc_b(tmp_path):
    """Create a test PDF with known content about quantum computing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Quantum computing uses qubits.")
    path = tmp_path / "doc_b.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def uploaded_sources(api_client, pdf_doc_a, pdf_doc_b):
    """Upload two test documents and return their source_ids. Cleanup on teardown."""
    source_ids = []
    try:
        with open(pdf_doc_a, "rb") as f:
            r = api_client.post(f"{BASE}/upload", files={"file": f}, timeout=30)
        assert r.status_code == 200, f"Upload A failed: {r.text}"
        source_a = r.json()["source_id"]
        source_ids.append(source_a)

        with open(pdf_doc_b, "rb") as f:
            r = api_client.post(f"{BASE}/upload", files={"file": f}, timeout=30)
        assert r.status_code == 200, f"Upload B failed: {r.text}"
        source_b = r.json()["source_id"]
        source_ids.append(source_b)

        yield source_a, source_b
    finally:
        for sid in source_ids:
            try:
                api_client.delete(f"{BASE}/sources/{sid}", timeout=10)
            except Exception:
                pass


def test_get_sources(api_client, uploaded_sources):
    """GET /sources returns both uploaded sources."""
    source_a, source_b = uploaded_sources
    r = api_client.get(f"{BASE}/sources", timeout=10)
    assert r.status_code == 200
    sources = r.json()["sources"]
    ids = {s["source_id"] for s in sources}
    assert source_a in ids, f"Source A ({source_a}) not found in /sources"
    assert source_b in ids, f"Source B ({source_b}) not found in /sources"


def test_ask_with_source_id_scoped(api_client, uploaded_sources):
    """Scoped /ask with source_id returns relevant content."""
    source_a, source_b = uploaded_sources

    # Query A about ML -> should know
    r = api_client.post(
        f"{BASE}/ask",
        params={"question": "What is machine learning?", "source_id": source_a},
        timeout=60,
    )
    assert r.status_code == 200
    answer = r.json()["answer"].lower()
    assert "machine learning" in answer or "artificial intelligence" in answer

    # Query A about quantum -> should NOT know (empty-context protection)
    r = api_client.post(
        f"{BASE}/ask",
        params={"question": "What is quantum computing?", "source_id": source_a},
        timeout=60,
    )
    assert r.status_code == 200
    answer = r.json()["answer"].lower()
    # Verify source isolation: Source B's unique content must NOT appear
    assert "quantum computing uses qubits" not in answer, f"Source B content leaked: {answer[:200]}"


def test_ask_without_source_id_global(api_client, uploaded_sources):
    """Global /ask without source_id works (backward compat)."""
    r = api_client.post(f"{BASE}/ask", params={"question": "test"}, timeout=60)
    assert r.status_code == 200
    assert len(r.json()["answer"]) > 20


def test_ask_nonexistent_source_id(api_client):
    """/ask with nonexistent source_id returns empty-context protection message."""
    r = api_client.post(
        f"{BASE}/ask", params={"question": "test", "source_id": "nonexistent123"}, timeout=30
    )
    assert r.status_code == 200
    answer = r.json()["answer"].lower()
    assert "couldn't find relevant information" in answer


def test_generate_notes_with_source_id(api_client, uploaded_sources):
    """Scoped notes generation with source_id."""
    source_a, _ = uploaded_sources
    r = api_client.post(
        f"{BASE}/generate-notes", json={"source_id": source_a}, timeout=60
    )
    assert r.status_code == 200
    notes = r.json()["notes"].lower()
    assert "machine learning" in notes or "artificial intelligence" in notes


def test_generate_notes_nonexistent_source_id(api_client):
    """Notes with nonexistent source_id returns empty-context message."""
    r = api_client.post(
        f"{BASE}/generate-notes", json={"source_id": "nonexistent123"}, timeout=30
    )
    assert r.status_code == 200
    notes = r.json()["notes"].lower()
    assert "no content found" in notes


def test_generate_notes_global(api_client):
    """Global notes generation works (backward compat)."""
    r = api_client.post(f"{BASE}/generate-notes", timeout=60)
    assert r.status_code == 200
    assert len(r.json()["notes"]) > 20


def test_generate_quiz_with_source_id(api_client, uploaded_sources):
    """Scoped quiz generation with source_id."""
    _, source_b = uploaded_sources
    r = api_client.post(
        f"{BASE}/generate-quiz", json={"source_id": source_b}, timeout=180
    )
    assert r.status_code == 200
    quiz = r.json()["quiz"].lower()
    assert "quantum" in quiz or "qubit" in quiz


def test_generate_quiz_global(api_client):
    """Global quiz generation works (backward compat)."""
    r = api_client.post(f"{BASE}/generate-quiz", timeout=180)
    assert r.status_code == 200
    assert len(r.json()["quiz"]) > 20


def test_delete_source(api_client, uploaded_sources):
    """DELETE /sources/{source_id} removes the source."""
    source_a, source_b = uploaded_sources

    r = api_client.delete(f"{BASE}/sources/{source_a}", timeout=10)
    assert r.status_code == 200

    r = api_client.get(f"{BASE}/sources", timeout=10)
    assert r.status_code == 200
    ids = {s["source_id"] for s in r.json()["sources"]}
    assert source_a not in ids, "Deleted source should not appear in /sources"
    assert source_b in ids, "Remaining source should still appear in /sources"


def test_delete_nonexistent_source(api_client):
    """DELETE nonexistent source returns 404."""
    r = api_client.delete(f"{BASE}/sources/nonexistent123", timeout=10)
    assert r.status_code == 404