import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import get_chroma


def seed_chroma():
    print("Seeding ChromaDB...")
    chroma_db = get_chroma()
    chroma_db.add_memory(
        "JARVIS is a personal AI assistant that helps with tasks, answers questions, and manages information.",
        metadata={"type": "system", "category": "identity"}
    )
    print(f"  [OK] ChromaDB: seed memory added (total: {chroma_db.count()})")


if __name__ == "__main__":
    seed_chroma()
