from typing import List

MAX_CHUNK_TOKENS = 300       # Target upper limit (~1200 characters)
WINDOW_CHUNK_TOKENS = 250    # Sliding window chunk size (~1000 characters)
OVERLAP_TOKENS = 25          # Overlap window (~100 characters)

def estimate_tokens(text: str) -> int:
    """Fast rule of thumb: ~4 characters per token in English."""
    return max(1, len(text) // 4)

def sliding_window_split(text: str, window_size: int = WINDOW_CHUNK_TOKENS, overlap: int = OVERLAP_TOKENS) -> List[str]:
    """Splits dense text into overlapping token windows."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + window_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start += (window_size - overlap)
    return chunks

def chunk_text(content: str) -> List[str]:
    """
    Adaptive Chunker:
    1. Splits on paragraph breaks (\n\n).
    2. If any paragraph exceeds MAX_CHUNK_TOKENS, applies sliding window fallback.
    """
    content = content.strip()
    if not content:
        return []

    raw_paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    final_chunks: List[str] = []

    for para in raw_paragraphs:
        if estimate_tokens(para) <= MAX_CHUNK_TOKENS:
            final_chunks.append(para)
        else:
            sub_chunks = sliding_window_split(para)
            final_chunks.extend(sub_chunks)

    return final_chunks