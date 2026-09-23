#!/usr/bin/env python
"""
Pilot script to ingest NCERT curriculum PDFs into the vector store.
Run with: python ingest_pilot.py
"""

import fitz
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from pdf_processor import extract_text_from_pdf, detect_chapters
from chunker import chunk_text, chunk_text_with_positions
from embedder import create_embeddings
from vector_store import store_chunks


def ingest_pdf(
    pdf_path: str,
    grade: int,
    subject: str,
    language: str,
    book_series: str,
    book_title: str,
    part: int,
    is_supplement: bool = False,
) -> str:
    """Ingest a single PDF with curriculum metadata."""
    print(f"\n=== Ingesting {pdf_path} ===")

    # Determine OCR language
    ocr_lang = "hin+eng" if language == "hi" else "eng"
    print(f"  Extracting text with ocr_lang={ocr_lang}...")

    text = extract_text_from_pdf(pdf_path, ocr_lang=ocr_lang)
    print(f"  Extracted {len(text)} characters")

    # Detect chapters/units in the text
    chapters = detect_chapters(text)
    print(f"  Detected {len(chapters)} chapter(s)/unit(s)")

    # Chunk the text with positions
    chunk_data = chunk_text_with_positions(text)
    chunks = [c[0] for c in chunk_data]
    positions = [c[1] for c in chunk_data]
    print(f"  Created {len(chunks)} chunks")

    # Assign chapter to each chunk based on position - overlap-aware assignment
    chapter_assignments = []
    for i, pos in enumerate(positions):
        chunk_start = pos
        chunk_text = chunks[i]
        chunk_end = chunk_start + len(chunk_text)

        assigned_chapter = None
        assigned_number = None

        # Find all chapters whose start_pos falls within or before this chunk
        applicable_chapters = []
        for ch in chapters:
            if ch["start_pos"] <= chunk_end:
                applicable_chapters.append(ch)
            else:
                break

        if applicable_chapters:
            # Assign the latest chapter that starts at or before chunk_end
            # If a chapter starts inside the chunk (start_pos > chunk_start), that chapter applies
            latest = applicable_chapters[-1]
            assigned_chapter = latest["title"]
            assigned_number = latest["number"]

        chapter_assignments.append((assigned_chapter, assigned_number))

    # Print chapter assignment summary
    chapter_counts = {}
    for ch_title, ch_num in chapter_assignments:
        key = f"Chapter {ch_num}" if ch_num else "Unassigned"
        chapter_counts[key] = chapter_counts.get(key, 0) + 1
    for k, v in chapter_counts.items():
        print(f"  {k}: {v} chunks")

    # Generate embeddings
    print("  Generating embeddings...")
    embeddings = create_embeddings(chunks)
    print(f"  Generated {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]}")

    # Store with curriculum metadata (per-chunk chapter assignment)
    filename = os.path.basename(pdf_path)
    source_id = store_chunks(
        chunks,
        embeddings,
        source_name=filename,
        source_type="pdf",
        owner_user_id=None,  # Curriculum has no owner
        source_kind="curriculum",
        grade=grade,
        subject=subject,
        language=language,
        book_series=book_series,
        book_title=book_title,
        part=part,
        is_supplement=is_supplement,
        chapter=[ca[0] for ca in chapter_assignments],
        chapter_number=[ca[1] for ca in chapter_assignments],
    )

    print(f"  Stored with source_id: {source_id}")
    return source_id


def main():
    """Ingest the two pilot NCERT PDFs."""

    pilot_files = [
        {
            "path": "NCERT/bhsr101.pdf",
            "grade": 1,
            "subject": "Hindi",
            "language": "hi",
            "book_series": "Bharati",
            "book_title": "Bharati Hindi Reader Class 1 Part 1",
            "part": 1,
            "is_supplement": False,
        },
        {
            "path": "NCERT/aemr101.pdf",
            "grade": 1,
            "subject": "English",
            "language": "en",
            "book_series": "Mridang",
            "book_title": "Mridang English Reader Class 1 Part 1",
            "part": 1,
            "is_supplement": False,
        },
    ]

    print("=== NCERT Curriculum Pilot Ingestion ===")
    print(f"Total PDFs to ingest: {2}")

    results = []
    for pdf_info in pilot_files:
        try:
            source_id = ingest_pdf(
                pdf_path=pdf_info["path"],
                grade=pdf_info["grade"],
                subject=pdf_info["subject"],
                language=pdf_info["language"],
                book_series=pdf_info["book_series"],
                book_title=pdf_info["book_title"],
                part=pdf_info["part"],
                is_supplement=pdf_info["is_supplement"],
            )
            results.append({
                "pdf": pdf_info["path"],
                "source_id": source_id,
                "status": "success"
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "pdf": pdf_info["path"],
                "status": "failed",
                "error": str(e)
            })

    print("\n=== Ingestion Summary ===")
    for r in results:
        if r["status"] == "success":
            print(f"  [OK] {r['pdf']} -> {r['source_id']}")
        else:
            print(f"  [FAIL] {r['pdf']} -> FAILED: {r['error']}")


if __name__ == "__main__":
    main()
