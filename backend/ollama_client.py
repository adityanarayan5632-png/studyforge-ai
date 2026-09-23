import os
import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


def ask_llm(prompt):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1024,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]