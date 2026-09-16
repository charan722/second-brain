from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import get_connection, init_db
from app.ingestion import ingest_note
from app.router import route_and_respond
from app.reflex import process_background_reflex

app = FastAPI(title="Local Second Brain API")

# Secure standard local CORS (disallows wildcards with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "null"  # Supports opening frontend directly as a local file (file://)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

class SaveNoteRequest(BaseModel):
    id: Optional[int] = None
    content: str

@app.post("/api/notes")
def save_note_endpoint(req: SaveNoteRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    note_id = ingest_note(content=req.content, note_id=req.id)
    return {"status": "success", "note_id": note_id}

@app.get("/api/notes")
def list_notes_endpoint():
    conn = get_connection()
    notes = conn.execute("SELECT id, content, created_at, source FROM notes ORDER BY id DESC;").fetchall()
    conn.close()
    return [dict(n) for n in notes]

@app.delete("/api/notes/{note_id}")
def delete_note_endpoint(note_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Purge vectors and chunks explicitly, then the note
    cursor.execute("BEGIN TRANSACTION;")
    cursor.execute("DELETE FROM vec_chunks WHERE chunk_id IN (SELECT id FROM chunks WHERE note_id = ?);", (note_id,))
    cursor.execute("DELETE FROM chunks WHERE note_id = ?;", (note_id,))
    cursor.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
    cursor.execute("COMMIT;")
    conn.close()
    return {"status": "deleted", "note_id": note_id}

@app.get("/api/tasks")
def list_tasks_endpoint():
    conn = get_connection()
    tasks = conn.execute("SELECT id, title, due_date, status, source_prompt, created_at FROM tasks ORDER BY due_date ASC;").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, bg_tasks: BackgroundTasks):
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    bg_tasks.add_task(process_background_reflex, user_msg)
    return route_and_respond(user_msg)