"""Curriculum grade authorization tests for M8.

Tests that curriculum retrieval uses the authenticated user's profile grade
and ignores client-provided grade parameter.
"""

import os
import pytest
import requests
from supabase import create_client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SECRET_KEY")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8002")

# Create Supabase admin client
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TEST_USER_GRADE1_EMAIL = "student_grade1_test@example.com"
TEST_USER_GRADE5_EMAIL = "student_grade5_test@example.com"
TEST_USER_NOGRADE_EMAIL = "student_nograde_test@example.com"
TEST_PASSWORD = "TestPass123!"


def create_test_user(email: str, grade: int = None) -> dict:
    """Create a test user via Supabase Admin API with optional grade in profile."""
    try:
        users = supabase_admin.auth.admin.list_users()
        for user in users:
            if user.email == email:
                supabase_admin.auth.admin.delete_user(user.id)
    except Exception:
        pass

    response = supabase_admin.auth.admin.create_user({
        "email": email,
        "password": TEST_PASSWORD,
        "email_confirm": True,
        "user_metadata": {"full_name": email.split("@")[0].title()}
    })
    user = response.user

    # Create profile with grade if provided
    if grade is not None:
        supabase_admin.table("profiles").insert({
            "id": user.id,
            "display_name": email.split("@")[0].title(),
            "grade": grade,
            "board": "CBSE"
        }).execute()

    return user


def sign_in_user(email: str) -> str:
    """Sign in a user and return access token."""
    response = supabase_admin.auth.sign_in_with_password({
        "email": email,
        "password": TEST_PASSWORD
    })
    return response.session.access_token


class TestCurriculumGradeAuthorization:
    """Tests for curriculum grade authorization."""

    token_grade1: str = ""
    token_grade5: str = ""
    token_nograde: str = ""
    user_grade1_id: str = ""
    user_grade5_id: str = ""
    user_nograde_id: str = ""

    @classmethod
    def setup_class(cls):
        print(f"\nCreating test users for grade authorization...")
        cls.user_grade1 = create_test_user(TEST_USER_GRADE1_EMAIL, grade=1)
        cls.user_grade5 = create_test_user(TEST_USER_GRADE5_EMAIL, grade=5)
        cls.user_nograde = create_test_user(TEST_USER_NOGRADE_EMAIL, grade=None)
        
        cls.user_grade1_id = cls.user_grade1.id
        cls.user_grade5_id = cls.user_grade5.id
        cls.user_nograde_id = cls.user_nograde.id
        
        print(f"Grade 1 user: {cls.user_grade1_id}")
        print(f"Grade 5 user: {cls.user_grade5_id}")
        print(f"No-grade user: {cls.user_nograde_id}")

        print("Signing in users...")
        cls.token_grade1 = sign_in_user(TEST_USER_GRADE1_EMAIL)
        cls.token_grade5 = sign_in_user(TEST_USER_GRADE5_EMAIL)
        cls.token_nograde = sign_in_user(TEST_USER_NOGRADE_EMAIL)
        print("Tokens obtained")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_grade1_user_can_access_grade1_curriculum(self):
        """Grade 1 user can access Grade 1 curriculum."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true"},
            headers=self._headers(self.token_grade1),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "onboarding" not in answer
        assert "profile grade" not in answer
        print(f"Grade 1 user curriculum query: {answer[:100]}...")

    def test_client_grade_is_ignored_profile_grade_used(self):
        """Verify client-provided grade is ignored and profile grade is used."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true", "grade": 5},
            headers=self._headers(self.token_grade1),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "onboarding" not in answer
        assert "profile grade" not in answer
        print(f"Grade 1 user with client grade=5: {answer[:100]}...")

    def test_grade5_user_client_grade_ignored(self):
        """Grade 5 user's client grade is ignored, profile grade used."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true", "grade": 1},
            headers=self._headers(self.token_grade5),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "onboarding" not in answer
        assert "profile grade" not in answer
        print(f"Grade 5 user with client grade=1: {answer[:100]}...")

    def test_user_without_profile_grade_gets_400(self):
        """User without profile grade gets 400 error when accessing curriculum."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true"},
            headers=self._headers(self.token_nograde),
            timeout=60
        )
        assert r.status_code == 400
        response_data = r.json()
        assert "onboarding" in response_data.get("detail", "").lower() or "grade" in response_data.get("detail", "").lower()
        print(f"No-grade user: {r.json()}")

    def test_normal_user_retrieval_unaffected(self):
        """Normal private user retrieval (use_curriculum=false) remains unaffected."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is machine learning?", "use_curriculum": "false"},
            headers=self._headers(self.token_grade1),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "onboarding" not in answer
        assert "profile grade" not in answer
        print(f"Normal retrieval for Grade 1 user: {answer[:100]}...")

    def test_curriculum_query_without_grade_param_uses_profile_grade(self):
        """Curriculum query without explicit grade param uses profile grade."""
        r = requests.post(
            f"{API_BASE}/ask",
            params={"question": "What is in the curriculum?", "use_curriculum": "true"},
            headers=self._headers(self.token_grade1),
            timeout=60
        )
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        assert "onboarding" not in answer
        print(f"Grade 1 user without explicit grade param: {answer[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=120"])