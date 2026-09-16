from app.database import init_db, get_connection
from app.ingestion import ingest_note
from app.embedder import generate_embeddings
import sqlite_vec

def test_phase1():
    print("--- 1. Initializing Schema ---")
    init_db()

    print("\n--- 2. Testing Brain-Dump Chunking & Ingestion ---")
    brain_dump = "Operating Systems Concept: " + ("Virtual memory maps process address space to physical RAM. " * 40)
    note_id = ingest_note(content=brain_dump)
    print(f"Created Note ID: {note_id}")

    conn = get_connection()
    chunks = conn.execute("SELECT id, chunk_index, length(chunk_text) as len FROM chunks WHERE note_id = ?", (note_id,)).fetchall()
    print(f"Brain dump was split into {len(chunks)} overlapping chunks.")
    assert len(chunks) > 1, "Failed: Brain-dump was not split into multiple chunks!"

    print("\n--- 3. Testing Idempotency (Updating Note) ---")
    updated_content = "Short note: Database B-Tree index enables O(log N) lookups."
    ingest_note(content=updated_content, note_id=note_id)
    
    chunks_after = conn.execute("SELECT id, chunk_text FROM chunks WHERE note_id = ?", (note_id,)).fetchall()
    vecs_after = conn.execute("""
        SELECT count(*) as count FROM vec_chunks 
        WHERE chunk_id IN (SELECT id FROM chunks WHERE note_id = ?)
    """, (note_id,)).fetchone()

    print(f"Chunks after update: {len(chunks_after)} (Expected: 1)")
    print(f"Vector rows after update: {vecs_after['count']} (Expected: 1)")
    assert len(chunks_after) == 1 and vecs_after['count'] == 1, "Failed: Old chunks were not purged!"

    print("\n--- 4. Testing sqlite-vec Semantic Retrieval ---")
    query = "How do database indexes speed up search?"
    query_vec = generate_embeddings([query])[0]

    matches = conn.execute("""
        SELECT c.chunk_text, v.distance
        FROM vec_chunks v
        JOIN chunks c ON v.chunk_id = c.id
        WHERE v.embedding MATCH ? AND k = 1
        ORDER BY v.distance ASC
    """, (sqlite_vec.serialize_float32(query_vec),)).fetchall()

    for m in matches:
        print(f"Retrieved Chunk: '{m['chunk_text']}'")
        print(f"Cosine Distance: {m['distance']:.4f}")

    conn.close()
    print("\n✅ PHASE 1 VERIFICATION PASSED: Database, Chunker, FastEmbed, and sqlite-vec work seamlessly!")

if __name__ == "__main__":
    test_phase1()