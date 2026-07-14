import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.sqlite_memory import SQLiteMemory


def init_databases():
    print("Initializing databases...")

    db = SQLiteMemory()
    cursor = db.conn.execute("SELECT COUNT(*) as cnt FROM conversations")
    count = cursor.fetchone()["cnt"]
    if count > 1:
        db.conn.execute("DELETE FROM messages")
        db.conn.execute("DELETE FROM conversations")
        db.conn.execute("DELETE FROM preferences")
        db.conn.commit()
        print("  [OK] Cleaned up duplicate seed data")

    conv_id = db.create_conversation(title="JARVIS Session")
    db.add_message(conv_id, "system", "JARVIS memory system initialized")
    db.add_message(conv_id, "assistant", "Hello, I am JARVIS. I am ready to assist you, Mr. Mohammed Areeb.")
    print(f"  [OK] SQLite: seed conversation created (id={conv_id})")

    db.set_preference("assistant_name", "JARVIS")
    db.set_preference("user_name", "Mohammed Areeb")
    db.set_preference("language", "en")
    print(f"  [OK] SQLite: default preferences stored at data/conversations.db")

    model_path = os.path.expanduser("~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz")
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path)
        if file_size > 80_000_000:
            try:
                from memory.chroma_memory import ChromaMemory
                cm = ChromaMemory()
                existing = cm.get_all_memories()
                if not existing:
                    cm.add_memory(
                        "JARVIS is a personal AI assistant that helps Mohammed Areeb with tasks, coding, and project management.",
                        metadata={"type": "system", "category": "identity"}
                    )
                print(f"  [OK] ChromaDB: ready at data/chroma/ ({cm.count()} memories)")
            except Exception:
                print("  [..] ChromaDB: model file exists but not ready yet")
        else:
            print("  [..] ChromaDB: model still downloading")
    else:
        print("  [..] ChromaDB: model not yet downloaded (seeding deferred)")

    db.close()
    print("\nDone.")


if __name__ == "__main__":
    init_databases()
