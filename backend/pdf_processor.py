"""
Language-agnostic PDF text extraction with OCR fallback.

Strategy:
1. Try native text extraction first (PyMuPDF) - preserves Unicode where available
2. Detect extraction quality issues (high replacement char ratio, suspicious patterns)
3. Fall back to OCR (Tesseract) for scanned/image-based or garbled PDFs
4. Preserve page boundaries for better chunking context
"""

import fitz
import pytesseract
from PIL import Image
import io
import re
import os


def _is_extraction_poor(text: str, min_length: int = 50) -> bool:
    """
    Heuristic to detect poor quality text extraction.

    Returns True if:
    - Text is too short (likely scanned/image PDF)
    - High ratio of replacement characters (U+FFFD) or suspicious patterns
    - Excessive repeated characters (e.g., font mapping issues)
    """
    if not text or len(text.strip()) < min_length:
        return True

    # Count Unicode replacement characters (often indicate encoding issues)
    replacement_count = text.count('\ufffd')
    if replacement_count > len(text) * 0.1:  # > 10% replacement chars
        return True

    # Count middle dots (· U+00B7) - common symptom of broken Devanagari font mapping
    middle_dot_count = text.count('\u00b7')
    if middle_dot_count > len(text) * 0.1:  # > 10% middle dots
        return True

    # Check for excessive repetition of same non-ASCII char (font mapping issue)
    non_ascii_chars = [c for c in text if ord(c) > 127]
    if non_ascii_chars:
        from collections import Counter
        char_counts = Counter(non_ascii_chars)
        most_common = char_counts.most_common(1)[0][1]
        if most_common > len(non_ascii_chars) * 0.5:  # One char dominates
            return True

    return False


def _ocr_page(page: fitz.Page, dpi: int = 300, lang: str = "eng") -> str:
    """
    Render page as image and extract text via Tesseract OCR.

    Args:
        page: PyMuPDF page object
        dpi: Rendering DPI (higher = better OCR, slower)
        lang: Tesseract language code(s), e.g., "eng", "hin+eng"

    Returns:
        Extracted text string
    """
    pix = page.get_pixmap(dpi=dpi)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Preprocess for better OCR
    # Convert to grayscale
    if img.mode != "L":
        img = img.convert("L")

    # Increase contrast slightly
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # Run OCR with PSM 4 (single column) as primary, PSM 3 as fallback
    # PSM 4 works better for sparse/columnar text than PSM 6 (uniform block)
    def _run_ocr(psm: int) -> str:
        try:
            text = pytesseract.image_to_string(img, lang=lang, config=f"--psm {psm}")
            return text.strip()
        except pytesseract.TesseractError:
            return ""

    # Try PSM 4 (single column) first - works best for sparse/columnar text
    text = _run_ocr(4)

    # If PSM 4 returns very little text, try PSM 3 (fully automatic)
    if len(text) < 20:
        text = _run_ocr(3)

    return text


def extract_text_from_pdf(pdf_path: str, ocr_lang: str = "eng") -> str:
    """
    Extract text from PDF with automatic OCR fallback for poor extractions.

    Args:
        pdf_path: Path to PDF file
        ocr_lang: Tesseract language code for OCR fallback (default: "eng")
                  Use "hin+eng" for Hindi+English, "eng" for English only

    Returns:
        Extracted text with page boundaries preserved (formatted as "=== PAGE N ===\n{text}")
    """
    doc = fitz.open(pdf_path)
    all_pages_text = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        # Try native extraction first
        native_text = page.get_text("text")

        # Check if native extraction is poor
        if _is_extraction_poor(native_text):
            # Fall back to OCR
            ocr_text = _ocr_page(page, dpi=300, lang=ocr_lang)
            # If OCR returns very little text, native is often better for sparse pages
            page_text = ocr_text if len(ocr_text) > len(native_text) else native_text
        else:
            page_text = native_text

        # Preserve page boundary for context
        if page_text.strip():
            all_pages_text.append(f"=== PAGE {page_num + 1} ===\n{page_text.strip()}")

    doc.close()

    return "\n\n".join(all_pages_text)


# Backward compatibility
def extract_text_from_pdf_simple(pdf_path: str) -> str:
    """Original simple extraction (kept for backward compatibility)."""
    return extract_text_from_pdf(pdf_path, ocr_lang="eng")


def detect_chapters(text: str) -> list:
    """
    Detect chapter/unit boundaries in extracted textbook text.

    Strategy:
    1. First try TOC-based detection for NCERT-style textbooks:
       - Find end-of-book Contents/TOC section
       - Parse Unit/Chapter entries with printed page numbers
       - Map printed pages to extracted page positions
       - Return boundaries at actual content start positions
    2. Fall back to regex-based detection for other documents.

    Returns:
        List of dicts with chapter info: {title, number, start_pos}
    """
    import re

    # Try TOC-based detection first (NCERT-style structure)
    toc_chapters = _detect_chapters_from_toc(text)
    if toc_chapters:
        return toc_chapters

    # Fallback: original regex-based detection
    return _detect_chapters_regex(text)


def _detect_chapters_from_toc(text: str) -> list:
    """
    Detect chapters by parsing end-of-book Table of Contents and mapping
    TOC entries to actual content boundaries.

    NCERT textbooks have a consistent structure:
    - Front matter
    - "About the Book" / teacher guide section
    - Actual lesson content
    - End-of-book Contents/TOC with Unit/Chapter entries and printed page numbers

    This function:
    1. Parses TOC for structured entries: (unit_number, title, printed_page)
    2. Maps printed page numbers to actual "=== PAGE N ===" positions
    3. For each TOC entry, searches forward from the mapped page to find
       the actual content start by matching the title
    4. Returns boundaries at those verified content start positions
    """
    import re
    from difflib import SequenceMatcher

    # Find page markers and their positions
    page_markers = []
    for match in re.finditer(r'=== PAGE (\d+) ===', text):
        page_markers.append({
            'page_num': int(match.group(1)),
            'position': match.start(),
        })

    if not page_markers:
        return []

    # Find TOC position
    last_toc_pos = _find_toc_position(text)
    if last_toc_pos == -1:
        return []

    # Parse TOC into structured entries with printed page numbers
    toc_entries = _parse_toc_entries(text, last_toc_pos)
    if not toc_entries:
        return []

    # Find content zone start (for validation)
    content_start_pos = _find_content_start(text, last_toc_pos)
    if content_start_pos == -1:
        return []

    # Map TOC entries to actual content boundaries
    chapters = []
    page_map = {pm['page_num']: pm['position'] for pm in page_markers}

    # Get list of content zone page markers (pages within content zone)
    content_pages = [pm for pm in page_markers if pm['position'] >= content_start_pos and pm['position'] < last_toc_pos]

    # First pass: try title matching for each unit
    raw_positions = {}
    for entry in toc_entries:
        unit_num = entry['number']
        title = entry['title']
        printed_page = entry['printed_page']

        # Find starting search position
        target_page_pos = None

        if printed_page is not None and printed_page in page_map:
            target_page_pos = page_map[printed_page]
        elif printed_page is not None:
            # If exact page not found, search nearby pages
            for offset in range(-3, 4):
                check_page = printed_page + offset
                if check_page in page_map:
                    target_page_pos = page_map[check_page]
                    break

        # If no printed page or page not found, use content zone start as base
        # and we'll search for the title from there
        if target_page_pos is None:
            target_page_pos = content_start_pos

        # Search forward from the target page for the actual content start
        # by matching the title against the extracted text
        content_start = _find_content_start_for_title(
            text, target_page_pos, title, last_toc_pos
        )

        if content_start is None:
            # Fallback: use the target page position
            content_start = target_page_pos

        # Store raw position (may have duplicates)
        raw_positions[unit_num] = content_start

    # Second pass: resolve duplicate positions
    # If multiple units have the same position, distribute them across content zone
    chapters = []
    assigned_positions = {}

    # Process units in TOC order (chronological)
    for entry in toc_entries:
        unit_num = entry['number']
        raw_pos = raw_positions.get(unit_num, content_start_pos)

        # Check if this position is already assigned to another unit
        if raw_pos in assigned_positions:
            # Position conflict - will be resolved in redistribution pass
            assigned_positions.setdefault(raw_pos, []).append(unit_num)
        else:
            assigned_positions[raw_pos] = [unit_num]

    # Redistribute conflicting units across content zone
    # Sort positions and assign units to available content pages
    conflict_positions = {pos: units for pos, units in assigned_positions.items() if len(units) > 1}

    if conflict_positions:
        # Redistribute: assign units to distinct content pages in TOC order
        # Use content_pages to get distinct page boundaries
        sorted_conflicts = sorted(conflict_positions.keys())
        all_conflicting_units = []
        for pos in sorted_conflicts:
            all_conflicting_units.extend(conflict_positions[pos])

        # Remove conflicting units from raw_positions so they get reassigned
        for units in conflict_positions.values():
            for u in units:
                raw_positions.pop(u, None)

        # Reassign conflicting units to distinct content pages
        # Distribute them across available content pages
        if content_pages and all_conflicting_units:
            # Use content_pages as anchor points
            step = max(1, len(content_pages) // max(1, len(all_conflicting_units)))
            for i, unit_num in enumerate(all_conflicting_units):
                page_idx = min(i * step, len(content_pages) - 1)
                raw_positions[unit_num] = content_pages[page_idx]['position']

    # Build final chapters list
    for entry in toc_entries:
        unit_num = entry['number']
        final_pos = raw_positions.get(unit_num, content_start_pos)

        # Validate: boundary must be in content zone, not in TOC
        if final_pos >= content_start_pos and final_pos < last_toc_pos:
            chapters.append({
                'title': f"Unit {unit_num}",
                'number': unit_num,
                'start_pos': final_pos,
            })

    # Sort by position to ensure chronological order
    chapters.sort(key=lambda c: c['start_pos'])

    # Deduplicate by number (keep first occurrence)
    seen = set()
    unique = []
    for c in chapters:
        if c['number'] not in seen:
            seen.add(c['number'])
            unique.append(c)

    if not unique:
        return []

    return unique


def _parse_toc_entries(text: str, toc_start: int) -> list:
    """
    Parse the TOC section into structured entries.
    Returns list of dicts: {number, title, printed_page}
    Handles hierarchical TOC where units don't have direct page numbers
    (page numbers are on lesson/chapter lines).
    """
    import re

    toc_section = text[toc_start:]
    lines = toc_section.split('\n')

    entries = []

    # First pass: find all lines that look like unit/chapter headings
    # These typically contain "Unit X", "Chapter X", "इकाई X", "अध्याय X" etc.
    # but NOT lesson-level entries (which have page numbers at the end)

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Match unit/chapter heading patterns
        # "Unit 1: My Family and Me"
        # "इकाई 1: शीर्षक"
        # "Chapter 1"
        # "bdkbZ 1:" (OCR artifact for "अध्याय")
        unit_match = re.search(
            r'(?:unit|यूनिट|इकाई|chapter|चैप्टर|अध्याय|bdkbz|lesson|पाठ|part|भाग)\s*(\d+)\s*[:.\-]?\s*(.*)',
            line, re.IGNORECASE
        )
        if not unit_match:
            continue

        unit_num = int(unit_match.group(1))
        title = unit_match.group(2).strip()

        # Filter out lesson-level entries (they have page numbers at end)
        # Lesson entries typically end with a page number
        # Unit headings typically don't have trailing page numbers
        if re.search(r'\d+\s*$', line.strip()):
            # This line ends with a number - likely a lesson entry, skip
            continue

        # Also filter out very short titles (likely fragments)
        if len(title) < 3:
            # Try to get title from next non-empty line if it doesn't look like a lesson
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.search(r'\d+\s*$', next_line):
                    title = next_line

        if len(title) < 3:
            title = f"Unit {unit_num}"

        # Extract printed page if available (sometimes in TOC)
        # Look for page number in this line or nearby lines
        printed_page = None
        numbers = re.findall(r'\d+', line)
        if numbers:
            # The last number might be a page number, but be careful
            # For unit headings without page numbers, this might pick up unit number
            pass

        entries.append({
            'number': unit_num,
            'title': title,
            'printed_page': printed_page,
        })

    # If no entries found with the strict approach, try a more lenient one
    if not entries:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            unit_match = re.search(
                r'(?:unit|यूनिट|इकाई|chapter|चैप्टर|अध्याय|lesson|पाठ|part|भाग)\s*(\d+)',
                line, re.IGNORECASE
            )
            if unit_match:
                unit_num = int(unit_match.group(1))
                # Extract title after the unit indicator
                title_start = unit_match.end()
                title = line[title_start:].strip()
                title = re.sub(r'^[:.\-\s]+', '', title)

                # Skip if ends with page number (lesson entry)
                if re.search(r'\d+\s*$', line.strip()):
                    continue

                if len(title) < 3:
                    title = f"Unit {unit_num}"

                entries.append({
                    'number': unit_num,
                    'title': title,
                    'printed_page': None,
                })

    # Deduplicate by unit number (keep first)
    seen = set()
    unique = []
    for e in entries:
        if e['number'] not in seen:
            seen.add(e['number'])
            unique.append(e)

    return unique


def _find_content_start_for_title(text: str, start_pos: int, title: str, toc_pos: int) -> int:
    """
    Search forward from start_pos to find where the actual content for this title begins.
    Uses fuzzy matching to handle OCR differences.
    """
    import re
    from difflib import SequenceMatcher

    # Normalize title for comparison
    norm_title = _normalize_for_matching(title)
    if len(norm_title) < 3:
        return start_pos

    # Search in a window forward from start_pos (up to 15 pages or toc_pos)
    search_end = min(len(text), toc_pos)
    search_text = text[start_pos:search_end]

    # Split into page sections
    page_splits = re.split(r'(=== PAGE \d+ ===)', search_text)

    # Reconstruct pages with their markers
    pages = []
    current_pos = start_pos
    current_content = ""
    current_marker = ""

    for part in page_splits:
        if re.match(r'=== PAGE \d+ ===', part):
            if current_content:
                pages.append({'marker': current_marker, 'content': current_content, 'pos': current_pos})
            current_marker = part
            current_content = ""
            # Find the absolute position of this marker
            marker_match = re.search(r'PAGE (\d+)', part)
            if marker_match:
                current_pos = text.find(part, current_pos)
        else:
            current_content += part

    if current_content:
        pages.append({'marker': current_marker, 'content': current_content, 'pos': current_pos})

    # For each page, try to match the title
    best_match = None
    best_score = 0.0

    for page in pages[:15]:  # Search up to 15 pages forward
        page_content = page['content']
        page_pos = page['pos']

        if not page_content or page_pos is None:
            continue

        # Normalize page content
        norm_content = _normalize_for_matching(page_content[:2000])  # First 2000 chars

        # Try to find title in content using fuzzy matching
        # Check if title words appear in sequence
        score = _fuzzy_title_match(norm_title, norm_content)

        if score > best_score and score > 0.4:  # Threshold for match
            best_score = score
            best_match = page_pos

    if best_match is not None:
        return best_match

    return start_pos


def _normalize_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, remove punctuation, collapse whitespace."""
    import re
    # Remove punctuation except spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    # Lowercase
    return text.lower().strip()


def _fuzzy_title_match(title: str, content: str) -> float:
    """
    Check if title words appear in content in order.
    Returns similarity score 0.0-1.0.
    """
    title_words = title.split()
    if not title_words:
        return 0.0

    content_words = content.split()
    if not content_words:
        return 0.0

    # Find longest subsequence of title words appearing in content in order
    matched = 0
    content_idx = 0

    for tw in title_words:
        # Find this word in content starting from current index
        found = False
        for i in range(content_idx, len(content_words)):
            # Fuzzy word match
            if _words_similar(tw, content_words[i]):
                matched += 1
                content_idx = i + 1
                found = True
                break
        if not found:
            break

    if matched == 0:
        return 0.0

    return matched / len(title_words)


def _words_similar(w1: str, w2: str) -> bool:
    """Check if two words are similar (handle OCR differences)."""
    if w1 == w2:
        return True
    if len(w1) < 3 or len(w2) < 3:
        return w1 == w2
    # Allow 1 char difference for short words, 2 for longer
    from difflib import SequenceMatcher
    return SequenceMatcher(None, w1, w2).ratio() > 0.8


def _find_toc_position(text: str) -> int:
    """
    Find the start position of the end-of-book TOC.
    Tries multiple strategies for English and Hindi PDFs.
    """
    import re

    # Strategy 1: Standard TOC markers (English + Hindi)
    toc_markers = [
        'contents',
        'विषय-सूची',
        'विषय सूची',
        'अनुक्रमणिका',
        'अनुक्रम',
        'सूची',
        'index',
        'table of contents',
    ]

    for marker in toc_markers:
        matches = list(re.finditer(rf'\b{re.escape(marker)}\b', text, re.IGNORECASE))
        if matches:
            return matches[-1].start()  # Last occurrence = end-of-book TOC

    # Strategy 2: If no standard marker, find TOC by detecting dense cluster
    # of unit/chapter references in the last 20% of the document
    # (TOC has many "Unit X" / "इकाई X" references close together)
    doc_len = len(text)
    search_start = int(doc_len * 0.8)
    last_section = text[search_start:]

    # Find all unit/chapter references in last section
    unit_refs = []
    for match in re.finditer(
        r'(?:unit|यूनिट|इकाई|chapter|चैप्टर|अध्याय|lesson|पाठ|part|भाग)\s*\d+',
        last_section, re.IGNORECASE
    ):
        unit_refs.append(search_start + match.start())

    if len(unit_refs) >= 3:  # TOC has multiple unit refs clustered
        # TOC starts at the first of this cluster
        return unit_refs[0]

    # Strategy 3: For Hindi PDFs with garbled OCR, look for common OCR artifacts
    # "bdkbZ" = OCR artifact for "अध्याय" (chapter)
    # "bdkbZ 1:", "bdkbZ 2:" etc. appear in TOC
    search_start = int(doc_len * 0.7)
    last_section = text[search_start:]

    ocr_chapter_refs = []
    for match in re.finditer(r'bdkbZ\s*\d+', last_section, re.IGNORECASE):
        ocr_chapter_refs.append(search_start + match.start())

    if len(ocr_chapter_refs) >= 3:
        # TOC starts at the first of this cluster
        return ocr_chapter_refs[0]

    # Strategy 3: For Hindi PDFs with garbled OCR, look for dense numeric patterns
    # in the last 30% that might indicate a TOC (many page numbers close together)
    search_start = int(doc_len * 0.7)
    last_section = text[search_start:]

    # Count numbers per line in the last section
    lines = last_section.split('\n')
    number_dense_lines = []
    for i, line in enumerate(lines):
        numbers = re.findall(r'\d+', line)
        if len(numbers) >= 3:  # Line with multiple numbers (likely TOC)
            number_dense_lines.append(search_start + line.find(line.strip()[:10]))

    if len(number_dense_lines) >= 3:
        return min(number_dense_lines)

    return -1


def _find_content_start(text: str, toc_pos: int) -> int:
    """
    Find the start of actual lesson content (after front matter/teacher guide).
    """
    import re

    # Strategy 1: "About the Book" / teacher guide markers
    content_markers = [
        'about the book',
        'पुस्तक के बारे में',
        'पुस्तक परिचय',
        'about this book',
        'about the textbook',
        'पाठ्यपुस्तक के बारे में',
    ]

    for marker in content_markers:
        matches = list(re.finditer(rf'\b{re.escape(marker)}\b', text, re.IGNORECASE))
        if matches:
            # Use the last occurrence before TOC
            for m in reversed(matches):
                if m.start() < toc_pos:
                    return m.start()

    # Strategy 2: Foreword/Preface markers (content often starts after foreword)
    # Find the FIRST foreword in the document (early), not the last
    foreword_markers = [
        'foreword',
        'प्राक्कथन',
        'भूमिका',
        'preface',
        'आमुख',
    ]

    for marker in foreword_markers:
        matches = list(re.finditer(rf'\b{re.escape(marker)}\b', text, re.IGNORECASE))
        if matches:
            # Use the FIRST foreword (early in document), not the last
            # TOC often lists "Foreword" in its entries
            for m in matches:
                if m.start() < toc_pos and m.start() < len(text) * 0.5:  # Early in doc
                    # Content starts AFTER foreword - find next page marker
                    foreword_end = m.end()
                    page_match = re.search(r'=== PAGE \d+ ===', text[foreword_end:])
                    if page_match:
                        return foreword_end + page_match.start()
                    return foreword_end

    # Strategy 3: Use page 5 as heuristic (NCERT front matter is typically 4 pages)
    page5_match = re.search(r'=== PAGE 5 ===', text)
    if page5_match:
        return page5_match.start()

    # Strategy 4: 20% into document (after typical front matter)
    return int(len(text) * 0.2)


def _detect_chapters_regex(text: str) -> list:
    """Original regex-based chapter detection (fallback)."""
    import re

    patterns = [
        r'(?:chapter|चैप्टर|अध्याय)\s*(\d+)',  # Chapter X
        r'(?:unit|यूनिट|इकाई)\s*(\d+)',       # Unit X
        r'(?:lesson|पाठ)\s*(\d+)',             # Lesson X
        r'(?:part|भाग)\s*(\d+)',               # Part X
    ]

    chapters = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            chapters.append({
                "title": match.group(0),
                "number": int(match.group(1)),
                "start_pos": match.start(),
            })

    chapters.sort(key=lambda c: c["start_pos"])

    seen = set()
    unique = []
    for c in chapters:
        if c["number"] not in seen:
            seen.add(c["number"])
            unique.append(c)

    return unique