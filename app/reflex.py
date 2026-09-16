import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import ollama
from app.database import get_connection

MODEL_NAME = "qwen2.5-coder:7b"

def extract_task_from_message(user_message: str) -> Optional[Dict[str, Any]]:
    """
    Analyzes message with a fast, cheap prompt to extract structured task data.
    """
    prompt = f"""Analyze this message for any upcoming event, interview, deadline, or scheduled task.
Message: "{user_message}"

Respond ONLY with a valid JSON object matching this schema:
{{
  "is_task": true or false,
  "title": "short task name" or null,
  "days_from_now": integer or null,
  "confidence": "high" or "low"
}}
Rule: "confidence" must be "high" if phrasing is committal ("I have", "due on", "scheduled").
"confidence" must be "low" if phrasing is tentative or uncertain ("might", "thinking of", "maybe").
"""

    try:
        client = ollama.Client()
        res = client.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.0}
        )
        data = json.loads(res["message"]["content"])
        if data.get("is_task") and data.get("title"):
            return data
        return None
    except Exception as e:
        print(f"[Reflex] Extraction error: {e}")
        return None

def normalize_title(title: str) -> str:
    """Simplifies task titles for fuzzy deduplication."""
    return re.sub(r"[^a-zA-Z0-9 ]", "", title).strip().lower()

def process_background_reflex(user_message: str):
    """
    Background worker:
    1. Extracts task metadata via local LLM.
    2. Computes absolute timestamp using Python datetime.
    3. Gates status by confidence (confirmed vs tentative).
    4. Upserts: Updates existing task on match, else inserts new.
    """
    task_data = extract_task_from_message(user_message)
    if not task_data:
        return None

    title = task_data["title"].strip()
    days = task_data.get("days_from_now")
    confidence = task_data.get("confidence", "low")

    # Deterministic date calculation in Python
    now_utc = datetime.now(timezone.utc)
    if days is not None:
        due_dt = now_utc + timedelta(days=days)
        due_date_str = due_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        due_date_str = None

    status = "confirmed" if confidence == "high" else "tentative"
    created_at_str = now_utc.isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    # Deduplication check: see if a similar task title already exists
    norm_title = normalize_title(title)
    existing_tasks = cursor.execute("SELECT id, title FROM tasks;").fetchall()
    
    matched_id = None
    for row in existing_tasks:
        if normalize_title(row["title"]) == norm_title or norm_title in normalize_title(row["title"]):
            matched_id = row["id"]
            break

    if matched_id:
        # Update existing record
        cursor.execute("""
            UPDATE tasks 
            SET due_date = ?, status = ?, created_at = ?
            WHERE id = ?;
        """, (due_date_str, status, created_at_str, matched_id))
        action = f"UPDATED task {matched_id} ('{title}')"
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO tasks (title, due_date, status, created_at)
            VALUES (?, ?, ?, ?);
        """, (title, due_date_str, status, created_at_str))
        action = f"INSERTED new task ('{title}')"

    conn.commit()
    conn.close()
    return action