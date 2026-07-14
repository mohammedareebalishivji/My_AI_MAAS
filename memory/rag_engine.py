import os
import uuid
import chromadb
from chromadb.config import Settings
from datetime import datetime, timezone


class RAGEngine:
    def __init__(self, persist_dir="data/chroma"):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.knowledge = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        self.conversations = self.client.get_or_create_collection(
            name="conversation_memories",
            metadata={"hnsw:space": "cosine"}
        )

    def ingest_text(self, text, metadata=None, chunk_size=500, overlap=50):
        chunks = self._chunk_text(text, chunk_size, overlap)
        ids = []
        docs = []
        metas = []

        base_meta = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "type": "knowledge"
        }
        if metadata:
            base_meta.update(metadata)

        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_meta = {**base_meta, "chunk_index": i, "total_chunks": len(chunks)}
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append(chunk_meta)

        if ids:
            self.knowledge.add(documents=docs, metadatas=metas, ids=ids)
        return len(ids)

    def ingest_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in [".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".xml"]:
            return 0, f"Unsupported file type: {ext}"

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return 0, f"Error reading file: {e}"

        if not content.strip():
            return 0, "File is empty"

        num_chunks = self.ingest_text(
            content,
            metadata={"source": os.path.basename(filepath), "filepath": filepath}
        )
        return num_chunks, f"Ingested {num_chunks} chunks from {filepath}"

    def ingest_directory(self, dir_path, extensions=None):
        if extensions is None:
            extensions = [".txt", ".md", ".py", ".json", ".csv", ".log"]

        total_chunks = 0
        results = []
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "venv" and d != "__pycache__"]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in extensions:
                    fpath = os.path.join(root, fname)
                    count, msg = self.ingest_file(fpath)
                    total_chunks += count
                    if count > 0:
                        results.append(msg)

        return total_chunks, results

    def retrieve(self, query, n_results=5, collection="knowledge"):
        coll = self.knowledge if collection == "knowledge" else self.conversations
        if coll.count() == 0:
            return []

        results = coll.query(query_texts=[query], n_results=n_results)
        memories = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                if distance < 0.8:
                    memories.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "relevance": 1.0 - distance
                    })
        return memories

    def store_conversation(self, user_text, response_text):
        ts = datetime.now(tz=timezone.utc).isoformat()
        combined = f"User: {user_text}\nAssistant: {response_text}"
        doc_id = str(uuid.uuid4())
        self.conversations.add(
            documents=[combined],
            metadatas=[{"timestamp": ts, "type": "conversation", "role": "exchange"}],
            ids=[doc_id]
        )

    def search_conversations(self, query, n_results=5):
        return self.retrieve(query, n_results=n_results, collection="conversations")

    def _chunk_text(self, text, chunk_size, overlap):
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                split_point = max(last_period, last_newline)
                if split_point > chunk_size * 0.3:
                    chunk = text[start:start + split_point + 1]
                    end = start + split_point + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]

    def get_stats(self):
        return {
            "knowledge_chunks": self.knowledge.count(),
            "conversation_memories": self.conversations.count()
        }

    def clear_knowledge(self):
        self.client.delete_collection("knowledge_base")
        self.knowledge = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
