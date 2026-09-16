import re
from typing import Dict, Any, List
import ollama
import sqlite_vec
from ddgs import DDGS
from app.database import get_connection
from app.embedder import generate_embeddings

MODEL_NAME = "qwen2.5-coder:7b"

# -------------------------------------------------------------------
# 1. Cheap Pre-Retrieval Intent Classifier
# -------------------------------------------------------------------
def classify_intent(user_message: str) -> str:
    prompt = f"""Classify this user message into exactly one category: SCHEDULE, CONCEPT, or WEB.
SCHEDULE = asks about a specific date, deadline, scheduled event, interview, or appointment.
CONCEPT = asks about an idea, technical topic, or something written in personal notes.
WEB = requires current external facts, live news, or documentation not in personal notes.

Message: "{user_message}"
Respond with only the category word (SCHEDULE, CONCEPT, or WEB)."""

    try:
        client = ollama.Client()
        res = client.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0}
        )
        category = res["message"]["content"].strip().upper()
        for cat in ["SCHEDULE", "CONCEPT", "WEB"]:
            if cat in category:
                return cat
        return "CONCEPT"
    except Exception as e:
        print(f"Classifier error: {e}, falling back to CONCEPT")
        return "CONCEPT"

# -------------------------------------------------------------------
# 2. Branch Handlers
# -------------------------------------------------------------------
def retrieve_schedule(query: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, title, due_date, status 
        FROM tasks 
        ORDER BY due_date ASC
        LIMIT 5;
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def retrieve_concepts(query: str, top_k: int = 3) -> List[str]:
    conn = get_connection()
    query_vec = generate_embeddings([query])[0]
    
    matches = conn.execute("""
        SELECT c.chunk_text, v.distance
        FROM vec_chunks v
        JOIN chunks c ON v.chunk_id = c.id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance ASC
    """, (sqlite_vec.serialize_float32(query_vec), top_k)).fetchall()
    
    conn.close()
    return [m["chunk_text"] for m in matches]

def clean_web_query(query: str) -> str:
    """Strips meta commands like 'search web for' so search engines find real results."""
    cleaned = re.sub(r"(?i)^(search(\s+the)?\s+web\s+(for)?|google|look\s+up)\s*", "", query).strip()
    return cleaned if cleaned else query

def retrieve_web(query: str, max_results: int = 3) -> str:
    search_term = clean_web_query(query)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_term, max_results=max_results))
            if not results:
                return "No web results found."
            return "\n".join([f"- {r['title']}: {r['body']} (Link: {r['href']})" for r in results])
    except Exception as e:
        return f"Web search unavailable: {e}"

# -------------------------------------------------------------------
# 3. Cognitive Dispatcher & Context Synthesizer
# -------------------------------------------------------------------
def route_and_respond(user_message: str) -> Dict[str, Any]:
    intent = classify_intent(user_message)
    context_str = ""

    if intent == "SCHEDULE":
        tasks = retrieve_schedule(user_message)
        if tasks:
            context_str = "Scheduled Tasks / Events in Database:\n" + "\n".join(
                [f"- {t['title']} | Date: {t['due_date']} (Status: {t['status']})" for t in tasks]
            )
        else:
            context_str = "No tasks or events found in your scheduled calendar."

    elif intent == "CONCEPT":
        chunks = retrieve_concepts(user_message, top_k=3)
        if chunks:
            context_str = "Relevant Personal Notes:\n" + "\n\n".join(chunks)
        else:
            context_str = "No relevant personal notes found."

    elif intent == "WEB":
        web_data = retrieve_web(user_message)
        context_str = f"Live Web Search Results:\n{web_data}"

    synthesis_prompt = f"""You are a personal second-brain assistant.
Answer the user's question clearly using the provided grounded context.
Summarize key points from the context if it contains relevant facts.

--- CONTEXT ({intent}) ---
{context_str}
-------------------------

User Message: {user_message}
"""

    client = ollama.Client()
    res = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": synthesis_prompt}],
        options={"temperature": 0.2}
    )

    return {
        "reply": res["message"]["content"],
        "intent": intent,
        "raw_context": context_str
    }