from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import get_connection, init_db
from app.ingestion import ingest_note
from app.router import route_and_respond
from app.reflex import process_background_reflex

app = FastAPI(title="Local Second Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- 1. NOTE MANAGEMENT ---
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

# --- 2. TASKS & DEADLINES ---
@app.get("/api/tasks")
def list_tasks_endpoint():
    conn = get_connection()
    tasks = conn.execute("SELECT id, title, due_date, status, created_at FROM tasks ORDER BY due_date ASC;").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

# --- 3. CHAT & COGNITIVE ROUTER ---
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, bg_tasks: BackgroundTasks):
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Fire-and-forget: dispatch background reflex immediately
    bg_tasks.add_task(process_background_reflex, user_msg)

    # 2. Synchronous intent routing and answer synthesis
    result = route_and_respond(user_msg)
    return result