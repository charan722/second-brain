import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "notes_vault.db"

MODEL_NAME = os.getenv("SECOND_BRAIN_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))
VECTOR_DISTANCE_THRESHOLD = float(os.getenv("VECTOR_DISTANCE_THRESHOLD", "0.65"))
DEDUPE_SIMILARITY_THRESHOLD = 0.80