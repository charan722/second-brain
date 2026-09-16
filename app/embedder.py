from typing import List
from fastembed import TextEmbedding

_model = None

def get_embedder() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Encodes a list of text strings into 384-dim float lists."""
    if not texts:
        return []
    embedder = get_embedder()
    return [vec.tolist() for vec in embedder.embed(texts)]