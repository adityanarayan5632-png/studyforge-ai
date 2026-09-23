FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app.py .
COPY auth.py .
COPY chunker.py .
COPY embedder.py .
COPY notes_generator.py .
COPY pdf_processor.py .
COPY quiz_generator.py .
COPY rag_pipeline.py .
COPY vector_store.py .
COPY ollama_client.py .

COPY chroma_db ./chroma_db

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]