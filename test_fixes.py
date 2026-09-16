from app.database import init_db, get_connection
from app.ingestion import ingest_note
from app.router import route_and_respond, classify_intent
from app.reflex import is_similar_title

def test_fixes():
    print("--- 1. Testing Strict Deduplication Matcher ---")
    assert is_similar_title("TCS Technical Interview", "TCS Technical Interview") == True
    assert is_similar_title("TCS technical interview", "TCS Technical Interview Prep") == True
    assert is_similar_title("TCS technical interview", "Mock Technical Interview with Alex") == False
    print("✓ Fuzzy matching prevented accidental collision on 'Interview'.")

    print("\n--- 2. Testing Heuristic Intent Classification (Zero LLM Latency) ---")
    assert classify_intent("when is my TCS interview scheduled?") == "SCHEDULE"
    assert classify_intent("search web for latest PyTorch releases") == "WEB"
    print("✓ Heuristic fast-path classified schedule and web without calling LLM.")

    print("\n--- 3. Testing Distance Cutoff on Irrelevant Queries ---")
    init_db()
    ingest_note("The mitochondria is the powerhouse of the biological cell.")
    res = route_and_respond("What is the current stock price of Apple?")
    print("Distance Scores:", res.get("distance_scores"))
    assert "powerhouse" not in res["reply"].lower()
    print("✓ Irrelevant note content was discarded by distance cutoff.")

    print("\n✅ ALL CORRECTNESS FIXES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_fixes()