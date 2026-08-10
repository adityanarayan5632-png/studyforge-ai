from pdf_processor import extract_text_from_pdf
from chunker import chunk_text
from embedder import create_embeddings

pdf_path = "uploads/sample.pdf"

text = extract_text_from_pdf(pdf_path)

chunks = chunk_text(text)

embeddings = create_embeddings(chunks)

print(f"Chunks: {len(chunks)}")
print(f"Embeddings: {len(embeddings)}")
print(f"Embedding Dimension: {len(embeddings[0])}")