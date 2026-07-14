import sqlite3
import json
from datetime import datetime, timezone


class SQLiteMemory:
    def __init__(self, db_path="data/conversations.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
        """)
        self.conn.commit()

    def create_conversation(self, title=None):
        cursor = self.conn.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title or f"Conversation {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",)
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, conversation_id, role, content):
        self.conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        self.conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,)
        )
        self.conn.commit()

    def get_conversation(self, conversation_id):
        cursor = self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        )
        conv = cursor.fetchone()
        if not conv:
            return None
        cursor = self.conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,)
        )
        return dict(conv) | {"messages": [dict(row) for row in cursor.fetchall()]}

    def get_recent_conversations(self, limit=10):
        cursor = self.conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def set_preference(self, key, value):
        self.conn.execute(
            """INSERT INTO preferences (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, json.dumps(value))
        )
        self.conn.commit()

    def get_preference(self, key):
        cursor = self.conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return json.loads(row["value"]) if row else None

    def search_messages(self, query, limit=20):
        cursor = self.conn.execute(
            "SELECT m.*, c.title FROM messages m JOIN conversations c ON m.conversation_id = c.id WHERE m.content LIKE ? ORDER BY m.timestamp DESC LIMIT ?",
            (f"%{query}%", limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
