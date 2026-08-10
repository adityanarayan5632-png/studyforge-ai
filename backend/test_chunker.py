from pdf_processor import extract_text_from_pdf
from chunker import chunk_text

pdf_path = "uploads/sample.pdf"

text = extract_text_from_pdf(pdf_path)

chunks = chunk_text(text)

print(f"\nTotal Chunks: {len(chunks)}\n")

for i, chunk in enumerate(chunks[:3]):
    print(f"\n--- Chunk {i+1} ---\n")
    print(chunk[:500])