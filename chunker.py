"""Split documents into overlapping word-based chunks."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    source: str   # document name
    index: int    # position of the chunk inside the document
    text: str


def chunk_text(text, source, chunk_words=100, overlap=25):
    """Return overlapping chunks. Overlap keeps sentences that straddle a boundary retrievable."""
    if chunk_words <= 0 or overlap < 0 or overlap >= chunk_words:
        raise ValueError("need chunk_words > 0 and 0 <= overlap < chunk_words")
    words = text.split()
    step = chunk_words - overlap
    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + chunk_words]
        chunks.append(Chunk(source=source, index=len(chunks), text=" ".join(piece)))
        if start + chunk_words >= len(words):
            break
    return chunks
