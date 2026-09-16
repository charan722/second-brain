from datetime import datetime, timezone
from typing import Optional
import sqlite_vec
from app.database import get_connection
from app.chunker import chunk_text
from app.embedder import generate_embeddings

def ingest_note(content: str, note_id: Optional[int] = None, source: str = "manual") -> int:
    """
    Atomically ingests or updates a note.
    - If note_id is provided, purges prior chunks/embeddings (Idempotent).
    - Runs chunking -> local embedding -> transactional write.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        if note_id is None:
            cursor.execute(
                "INSERT INTO notes (content, created_at, source) VALUES (?, ?, ?);",
                (content, now_iso, source)
            )
            note_id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE notes SET content = ?, created_at = ?, source = ? WHERE id = ?;",
                (content, now_iso, source, note_id)
            )
            # Purge existing chunks to prevent duplicates
            cursor.execute("""
                DELETE FROM vec_chunks 
                WHERE chunk_id IN (SELECT id FROM chunks WHERE note_id = ?);
            """, (note_id,))
            cursor.execute("DELETE FROM chunks WHERE note_id = ?;", (note_id,))

        chunks = chunk_text(content)
        
        if chunks:
            vectors = generate_embeddings(chunks)

            for idx, (chunk_str, vector) in enumerate(zip(chunks, vectors)):
                cursor.execute(
                    "INSERT INTO chunks (note_id, chunk_text, chunk_index) VALUES (?, ?, ?);",
                    (note_id, chunk_str, idx)
                )
                chunk_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?);",
                    (chunk_id, sqlite_vec.serialize_float32(vector))
                )

        cursor.execute("COMMIT;")
        return note_id

    except Exception as e:
        cursor.execute("ROLLBACK;")
        raise RuntimeError(f"Ingestion failed and was rolled back: {e}")
    finally:
        conn.close()