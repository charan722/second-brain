import sqlite3
import sqlite_vec
from app.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT DEFAULT 'manual'
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT,
            status TEXT DEFAULT 'confirmed',
            source_note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
            source_prompt TEXT,
            created_at TEXT NOT NULL
        );
    """)
    
    # Safe migration if table already existed without source_prompt
    cursor.execute("PRAGMA table_info(tasks);")
    columns = [row["name"] for row in cursor.fetchall()]
    if "source_prompt" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN source_prompt TEXT;")
        
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_note_id ON chunks(note_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized & migrated successfully.")