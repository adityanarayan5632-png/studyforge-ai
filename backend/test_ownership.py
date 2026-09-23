"""Security tests for source ownership (Phase 2.5C-2).

Creates two Supabase test users, gets their access tokens,
and verifies ownership enforcement.
"""

import os
import tempfile
import pytest
import requests
import fitz
import uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# Configuration
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SECRET_KEY"]
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

# Create Supabase admin client
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

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

    # Create new user
    response = supabase_admin.auth.admin.create_user({
        "email": unique_email,
        "password": TEST_PASSWORD,
        "email_confirm": True,
        "user_metadata": {"full_name": unique_email.split("@")[0].title()}
    })
    return response.user


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
    page.insert_text((72, 72), content)
    path = tempfile.mktemp(suffix=".pdf")
    doc.save(path)
    doc.close()
    return path


class TestSourceOwnership:
    """Source ownership security tests."""

    # Class attributes to share state across tests
    source_a_id: str = ""
    source_b_id: str = ""
    token_a: str = ""
    token_b: str = ""

    @classmethod
    def setup_class(cls):
        """Set up test users and tokens."""
        print(f"\nCreating test users...")
        cls.user_a = create_test_user(TEST_USER_A_EMAIL)
        cls.user_b = create_test_user(TEST_USER_B_EMAIL)
        print(f"User A: {cls.user_a.id} ({cls.user_a.email})")
        print(f"User B: {cls.user_b.id} ({cls.user_b.email})")

        print("Signing in users...")
        cls.token_a = sign_in_user(cls.user_a.email)
        cls.token_b = sign_in_user(cls.user_b.email)
        print(f"Token A obtained: {cls.token_a[:20]}...")
        print(f"Token B obtained: {cls.token_b[:20]}...")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_upload_sources(self):
        """A uploads A.pdf, B uploads B.pdf."""
        # A uploads
        pdf_a = create_test_pdf("Document A - Machine Learning content")
        with open(pdf_a, "rb") as f:
            r = requests.post(f"{API_BASE}/upload", files={"file": f}, headers=self._headers(self.token_a), timeout=30)
        assert r.status_code == 200, f"A upload failed: {r.text}"
        TestSourceOwnership.source_a_id = r.json()["source_id"]
        print(f"A uploaded source: {TestSourceOwnership.source_a_id}")

        # B uploads
        pdf_b = create_test_pdf("Document B - Quantum Computing content")
        with open(pdf_b, "rb") as f:
            r = requests.post(f"{API_BASE}/upload", files={"file": f}, headers=self._headers(self.token_b), timeout=30)
        assert r.status_code == 200, f"B upload failed: {r.text}"
        TestSourceOwnership.source_b_id = r.json()["source_id"]
        print(f"B uploaded source: {TestSourceOwnership.source_b_id}")

    def test_get_sources_isolated(self):
        """A GET /sources → only A.pdf; B GET /sources → only B.pdf."""
        # A lists sources
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_a), timeout=10)
        assert r.status_code == 200, f"A list failed: {r.text}"
        sources_a = {s["source_id"] for s in r.json()["sources"]}
        assert TestSourceOwnership.source_a_id in sources_a, "A should see their own source"
        assert TestSourceOwnership.source_b_id not in sources_a, "A should NOT see B's source"
        print(f"A sees: {sources_a}")

        # B lists sources
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_b), timeout=10)
        assert r.status_code == 200, f"B list failed: {r.text}"
        sources_b = {s["source_id"] for s in r.json()["sources"]}
        assert TestSourceOwnership.source_b_id in sources_b, "B should see their own source"
        assert TestSourceOwnership.source_a_id not in sources_b, "B should NOT see A's source"
        print(f"B sees: {sources_b}")

    def test_cannot_delete_other_source(self):
        """A cannot delete B.pdf; B cannot delete A.pdf."""
        # A tries to delete B's source
        r = requests.delete(f"{API_BASE}/sources/{TestSourceOwnership.source_b_id}", headers=self._headers(self.token_a), timeout=10)
        assert r.status_code == 404, f"A deleting B should be 404, got {r.status_code}: {r.text}"

        # B tries to delete A's source
        r = requests.delete(f"{API_BASE}/sources/{TestSourceOwnership.source_a_id}", headers=self._headers(self.token_b), timeout=10)
        assert r.status_code == 404, f"B deleting A should be 404, got {r.status_code}: {r.text}"

    def test_can_delete_own_source(self):
        """A can delete A.pdf; B can delete B.pdf."""
        # A deletes their own source
        r = requests.delete(f"{API_BASE}/sources/{TestSourceOwnership.source_a_id}", headers=self._headers(self.token_a), timeout=10)
        assert r.status_code == 200, f"A deleting own source failed: {r.text}"

        # B deletes their own source
        r = requests.delete(f"{API_BASE}/sources/{TestSourceOwnership.source_b_id}", headers=self._headers(self.token_b), timeout=10)
        assert r.status_code == 200, f"B deleting own source failed: {r.text}"

        # Verify both are gone
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_a), timeout=10)
        sources_a = {s["source_id"] for s in r.json()["sources"]}
        assert TestSourceOwnership.source_a_id not in sources_a
        assert TestSourceOwnership.source_b_id not in sources_a

        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_b), timeout=10)
        sources_b = {s["source_id"] for s in r.json()["sources"]}
        assert TestSourceOwnership.source_a_id not in sources_b
        assert TestSourceOwnership.source_b_id not in sources_b

    def test_legacy_sources_not_exposed(self):
        """Legacy/unowned sources are not returned through authenticated /sources."""
        # Verify that legacy sources (without owner_user_id) are not returned
        # by checking that A doesn't see the legacy sources created by Phase 2 tests
        r = requests.get(f"{API_BASE}/sources", headers=self._headers(self.token_a), timeout=10)
        assert r.status_code == 200
        sources = r.json()["sources"]
        
        # All sources A sees should have owner_user_id == A's user_id
        for s in sources:
            assert s.get("owner_user_id") == TestSourceOwnership.user_a.id, \
                f"Legacy source exposed to A: {s}"
        print(f"A sees {len(sources)} sources, all owned by A")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=120"])