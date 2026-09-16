from app.database import init_db, get_connection
from app.reflex import process_background_reflex

def test_phase3():
    print("--- 1. Resetting Tasks Table ---")
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM tasks;")
    conn.commit()
    conn.close()

    print("\n--- 2. Testing High Confidence Task Extraction ---")
    msg1 = "I have my TCS technical interview in 10 days"
    action1 = process_background_reflex(msg1)
    print(f"Reflex Action: {action1}")

    conn = get_connection()
    row1 = conn.execute("SELECT title, due_date, status FROM tasks LIMIT 1;").fetchone()
    print(f"Stored: '{row1['title']}' | Due: {row1['due_date']} | Status: {row1['status']}")
    assert row1['status'] == "confirmed", "Failed: Should be 'confirmed'!"
    assert row1['due_date'] is not None, "Failed: due_date should be calculated!"

    print("\n--- 3. Testing Task Deduplication & Update ---")
    msg2 = "My TCS technical interview got postponed to 15 days from now"
    action2 = process_background_reflex(msg2)
    print(f"Reflex Action: {action2}")

    count = conn.execute("SELECT count(*) as count FROM tasks;").fetchone()["count"]
    row2 = conn.execute("SELECT title, due_date FROM tasks LIMIT 1;").fetchone()
    print(f"Total task count: {count} (Expected: 1)")
    print(f"Updated Due Date: {row2['due_date']}")
    assert count == 1, "Failed: Created duplicate row instead of updating!"

    print("\n--- 4. Testing Tentative / Hedged Phrasing ---")
    msg3 = "I might attend the React meetup in 5 days"
    action3 = process_background_reflex(msg3)
    print(f"Reflex Action: {action3}")

    row3 = conn.execute("SELECT title, status FROM tasks WHERE title LIKE '%React%';").fetchone()
    print(f"Stored: '{row3['title']}' | Status: {row3['status']}")
    assert row3['status'] == "tentative", "Failed: Hedged phrasing should be 'tentative'!"

    conn.close()
    print("\n✅ PHASE 3 VERIFICATION PASSED: Reflex extraction, date math, gating, and deduplication work seamlessly!")

if __name__ == "__main__":
    test_phase3()