from datetime import datetime, timezone
from app.database import get_connection, init_db
from app.ingestion import ingest_note
from app.router import route_and_respond

def test_phase2():
    print("--- 1. Setting up Sample Data ---")
    init_db()
    conn = get_connection()
    
    # Insert a sample structured task into episodic memory
    conn.execute("DELETE FROM tasks;")
    conn.execute("""
        INSERT INTO tasks (title, due_date, status, created_at)
        VALUES ('TCS Technical Interview', '2026-09-25 10:00:00', 'confirmed', ?);
    """, (datetime.now(timezone.utc).isoformat(),))
    conn.commit()
    conn.close()

    # Ingest a concept note into vector memory
    ingest_note(content="CAP theorem states that a distributed data store can simultaneously provide at most two of Consistency, Availability, and Partition tolerance.")

    print("\n--- 2. Testing SCHEDULE Branch ---")
    res_schedule = route_and_respond("When is my TCS interview scheduled?")
    print(f"Intent Detected: {res_schedule['intent']}")
    print(f"AI Answer:\n{res_schedule['reply']}\n")
    assert res_schedule['intent'] == "SCHEDULE", "Failed: Did not classify as SCHEDULE!"

    print("\n--- 3. Testing CONCEPT Branch ---")
    res_concept = route_and_respond("What does the CAP theorem state?")
    print(f"Intent Detected: {res_concept['intent']}")
    print(f"AI Answer:\n{res_concept['reply']}\n")
    assert res_concept['intent'] == "CONCEPT", "Failed: Did not classify as CONCEPT!"

    print("\n--- 4. Testing WEB Branch ---")
    res_web = route_and_respond("Search web for latest Python features")
    print(f"Intent Detected: {res_web['intent']}")
    print(f"AI Answer:\n{res_web['reply']}\n")
    assert res_web['intent'] == "WEB", "Failed: Did not classify as WEB!"

    print("✅ PHASE 2 VERIFICATION PASSED: Intent Routing & Context Synthesis are operational!")

if __name__ == "__main__":
    test_phase2()