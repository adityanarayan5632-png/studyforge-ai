#!/usr/bin/env python
"""
Focused tests for chapter assignment logic (M9.7 fix).
Tests the overlap-aware chapter assignment in m97_ingest.py.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pdf_processor import extract_text_from_pdf, detect_chapters
from chunker import chunk_text_with_positions


def assign_chapters(chunks, positions, chapters):
    """Replicate the chapter assignment logic from m97_ingest.py"""
    chapter_assignments = []
    for i, pos in enumerate(positions):
        chunk_start = pos
        chunk_text = chunks[i]
        chunk_end = chunk_start + len(chunk_text)

        assigned_chapter = None
        assigned_number = None

        applicable_chapters = []
        for ch in chapters:
            if ch['start_pos'] <= chunk_end:
                applicable_chapters.append(ch)
            else:
                break

        if applicable_chapters:
            latest = applicable_chapters[-1]
            assigned_chapter = latest['title']
            assigned_number = latest['number']

        chapter_assignments.append((assigned_chapter, assigned_number))
    return chapter_assignments


def test_chunk_after_chapter_boundary():
    """Chunk starts after chapter boundary -> assigns chapter."""
    chapters = [{'start_pos': 100, 'title': 'Chapter 1', 'number': 1}]
    chunks = ['Content after chapter']
    positions = [200]

    assignments = assign_chapters(chunks, positions, chapters)
    assert assignments == [('Chapter 1', 1)], f"Expected [('Chapter 1', 1)], got {assignments}"
    print("PASS: test_chunk_after_chapter_boundary")


def test_chapter_boundary_inside_chunk():
    """Chunk starts before first chapter but chapter boundary occurs inside chunk -> assigns chapter."""
    chapters = [{'start_pos': 100, 'title': 'Chapter 1', 'number': 1}]
    chunks = ['x' * 150]  # chunk spans 0-150, chapter at 100 is inside
    positions = [0]

    assignments = assign_chapters(chunks, positions, chapters)
    assert assignments == [('Chapter 1', 1)], f"Expected [('Chapter 1', 1)], got {assignments}"
    print("PASS: test_chapter_boundary_inside_chunk")


def test_chunk_before_any_chapter():
    """Chunk before any chapter boundary -> remains None."""
    chapters = [{'start_pos': 100, 'title': 'Chapter 1', 'number': 1}]
    chunks = ['x' * 50]  # chunk spans 0-50, chapter at 100 is after
    positions = [0]

    assignments = assign_chapters(chunks, positions, chapters)
    assert assignments == [(None, None)], f"Expected [(None, None)], got {assignments}"
    print("PASS: test_chunk_before_any_chapter")


def test_two_chapter_boundaries_in_one_chunk():
    """Two chapter boundaries inside one chunk -> assigns latest chapter."""
    chapters = [
        {'start_pos': 50, 'title': 'Chapter 1', 'number': 1},
        {'start_pos': 150, 'title': 'Chapter 2', 'number': 2}
    ]
    chunks = ['x' * 200]  # chunk spans 0-200, both chapters inside
    positions = [0]

    assignments = assign_chapters(chunks, positions, chapters)
    # Should assign the latest chapter that falls within the chunk
    assert assignments == [('Chapter 2', 2)], f"Expected [('Chapter 2', 2)], got {assignments}"
    print("PASS: test_two_chapter_boundaries_in_one_chunk")


def test_bhsr122_real_pdf():
    """bhsr122.pdf specifically: should get chapter_number=5."""
    text = extract_text_from_pdf('NCERT/bhsr122.pdf', ocr_lang='hin+eng')
    chapters = detect_chapters(text)
    chunk_data = chunk_text_with_positions(text)
    chunks = [c[0] for c in chunk_data]
    positions = [c[1] for c in chunk_data]

    assignments = assign_chapters(chunks, positions, chapters)

    # Should have exactly 1 chunk with chapter_number=5
    assert len(assignments) == 1, f"Expected 1 chunk, got {len(assignments)}"
    assert assignments[0] == ('\u0907\u0915\u093e\u0908 5', 5), f"Expected chapter 5, got {assignments[0]}"
    print("PASS: test_bhsr122_real_pdf")


def test_multiple_chunks_with_chapters():
    """Multiple chunks, chapters spanning across them."""
    chapters = [
        {'start_pos': 100, 'title': 'Chapter 1', 'number': 1},
        {'start_pos': 500, 'title': 'Chapter 2', 'number': 2}
    ]
    # 3 chunks: 0-300, 300-600, 600-900
    chunks = ['x' * 300, 'x' * 300, 'x' * 300]
    positions = [0, 300, 600]

    assignments = assign_chapters(chunks, positions, chapters)

    # Chunk 0 (0-300): chapter 1 at 100 is inside -> Ch1
    # Chunk 1 (300-600): chapter 2 at 500 is inside -> Ch2
    # Chunk 2 (600-900): no chapter starts in range, but latest is Ch2 -> Ch2
    expected = [('Chapter 1', 1), ('Chapter 2', 2), ('Chapter 2', 2)]
    assert assignments == expected, f"Expected {expected}, got {assignments}"
    print("PASS: test_multiple_chunks_with_chapters")


def test_no_chapters():
    """No chapters detected -> all assignments None."""
    chapters = []
    chunks = ['chunk1', 'chunk2']
    positions = [0, 100]

    assignments = assign_chapters(chunks, positions, chapters)
    assert assignments == [(None, None), (None, None)], f"Expected all None, got {assignments}"
    print("PASS: test_no_chapters")


if __name__ == '__main__':
    test_chunk_after_chapter_boundary()
    test_chapter_boundary_inside_chunk()
    test_chunk_before_any_chapter()
    test_two_chapter_boundaries_in_one_chunk()
    test_bhsr122_real_pdf()
    test_multiple_chunks_with_chapters()
    test_no_chapters()
    print("\nAll chapter assignment tests passed!")
