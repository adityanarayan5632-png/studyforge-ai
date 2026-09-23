from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text):
    """Split text into chunks, returning just the text."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks = splitter.split_text(text)
    return chunks


def chunk_text_with_positions(text):
    """Split text into chunks and return chunks with their start positions in the original text."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    # Use split_text to get chunks
    chunks = splitter.split_text(text)

    # Find actual positions of each chunk in the original text
    positions = []
    search_start = 0
    for chunk in chunks:
        # Find this chunk in the original text starting from search_start
        pos = text.find(chunk, search_start)
        if pos == -1:
            # Fallback: use search_start if chunk not found exactly
            pos = search_start
        positions.append(pos)
        # Next search should start after this chunk (accounting for overlap)
        search_start = pos + len(chunk) - 200  # account for 200 char overlap
        if search_start < 0:
            search_start = 0

    return list(zip(chunks, positions))