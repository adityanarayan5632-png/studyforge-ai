from pdf_processor import extract_text_from_pdf
from chunker import chunk_text
from embedder import create_embeddings
from vector_store import (
    store_chunks,
    get_collection_count
)

pdf_path = "uploads/sample.pdf"

text = extract_text_from_pdf(pdf_path)

chunks = chunk_text(text)

embeddings = create_embeddings(chunks)

store_chunks(chunks, embeddings)

print(
    f"Stored Chunks: {get_collection_count()}"
)