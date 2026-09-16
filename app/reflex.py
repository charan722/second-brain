import json
import re
from difflib import SequenceMatcher
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import ollama
from app.database import get_connection
from app.config import MODEL_NAME, OLLAMA_TIMEOUT, DEDUPE_SIMILARITY_THRESHOLD

def extract_task_from_message(user_message: str) -> Optional[Dict[str, Any]]:
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
        client = ollama.Client(timeout=OLLAMA_TIMEOUT)
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
        print(f"[Reflex] Extraction error/timeout: {e}")
        return None

def normalize_title(title: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 ]", "", title).strip().lower()

def is_similar_title(target: str, candidate: str, threshold: float = DEDUPE_SIMILARITY_THRESHOLD) -> bool:
    norm_target = normalize_title(target)
    norm_candidate = normalize_title(candidate)
    
    if norm_target == norm_candidate:
        return True
    
    ratio = SequenceMatcher(None, norm_target, norm_candidate).ratio()
    return ratio >= threshold

def process_background_reflex(user_message: str):
    task_data = extract_task_from_message(user_message)
    if not task_data:
        return None

    title = task_data["title"].strip()
    days = task_data.get("days_from_now")
    confidence = task_data.get("confidence", "low")

    now_utc = datetime.now(timezone.utc)
    due_date_str = (now_utc + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if days is not None else None
    status = "confirmed" if confidence == "high" else "tentative"
    created_at_str = now_utc.isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    existing_tasks = cursor.execute("SELECT id, title FROM tasks;").fetchall()
    matched_id = None
    for row in existing_tasks:
        if is_similar_title(title, row["title"]):
            matched_id = row["id"]
            break

    if matched_id:
        cursor.execute("""
            UPDATE tasks 
            SET due_date = ?, status = ?, source_prompt = ?, created_at = ?
            WHERE id = ?;
        """, (due_date_str, status, user_message, created_at_str, matched_id))
        action = f"UPDATED task {matched_id} ('{title}')"
    else:
        cursor.execute("""
            INSERT INTO tasks (title, due_date, status, source_prompt, created_at)
            VALUES (?, ?, ?, ?, ?);
        """, (title, due_date_str, status, user_message, created_at_str))
        action = f"INSERTED new task ('{title}')"

    conn.commit()
    conn.close()
    return action