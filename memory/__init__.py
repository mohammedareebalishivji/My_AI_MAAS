from .sqlite_memory import SQLiteMemory
from .rag_engine import RAGEngine

_chroma_instance = None


def get_chroma():
    global _chroma_instance
    if _chroma_instance is None:
        _chroma_instance = RAGEngine()
    return _chroma_instance
