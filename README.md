# JARVIS 2.0: Personal AI Assistant

JARVIS 2.0 is a highly modular, voice-controlled, and web-enabled personal AI assistant inspired by Iron Man's J.A.R.V.I.S. It integrates a local LLM brain, local speech-to-text (STT) ears, highly realistic text-to-speech (TTS) voices, database memory, RAG-based context injection, and system automation tools.

---

## 🌟 Key Features

- **🧠 Hybrid Brain Engine:** Powered by local Ollama models (such as Llama 3) with robust fallback or primary routing.
- **🎙️ Local STT (Ears):** Local background speech recognition utilizing OpenAI's Whisper model.
- **🗣️ Natural TTS (Voice):** Highly realistic voice generation powered by Coqui XTTS v2.
- **📂 Long-Term Memory (RAG):** Integrates ChromaDB for semantic search of past conversations and SQLite for relational memory storage.
- **⚙️ Skill Engine:** Automated skill classification and parameters extraction (e.g. running scripts, searching the web, controlling OS).
- **🕹️ Automation (Hands):** Hands-on OS automation capabilities utilizing `pyautogui`, `psutil`, and shell sub-processes.
- **🌐 Web Interface:** A premium, modern web dashboard communicating via FastAPI and WebSockets.

---

## 🏛️ Architecture & Modules

The system is highly modularized into specialized components:

- **[main.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/main.py):** Main entry point for the interactive CLI and Voice interface.
- **[server.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/server.py):** FastAPI backend exposing WebSocket connections, API endpoints, and handling lazy-loaded XTTS v2 TTS generations.
- **[brain.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/brain.py):** Interfaces with Ollama/LLM API, manages system prompts, injected contexts, and handles structured tool outputs.
- **[ears.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/ears.py):** Configures microphone listening, records voice input, and performs local transcription.
- **[voice.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/voice.py):** Synthesizes natural-sounding speech utilizing local TTS architectures.
- **[automation.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/automation.py):** Defines the "hands" (commands, mouse controls, active window information, text pasting, keyboard automation).
- **[skill_engine.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/skill_engine.py):** Automates parsing user intentions and matching them to custom script runs.
- **[memory/](file:///Users/areebalishivji/Desktop/My_AI_MAAS/memory):**
  - [sqlite_memory.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/memory/sqlite_memory.py): Stores conversation logs in SQLite.
  - [rag_engine.py](file:///Users/areebalishivji/Desktop/My_AI_MAAS/memory/rag_engine.py): Converts logs to vector embeddings using ChromaDB for context-aware chat retrieval.
- **[static/](file:///Users/areebalishivji/Desktop/My_AI_MAAS/static):** Contains UI static files ([index.html](file:///Users/areebalishivji/Desktop/My_AI_MAAS/static/index.html), [style.css](file:///Users/areebalishivji/Desktop/My_AI_MAAS/static/style.css), [app.js](file:///Users/areebalishivji/Desktop/My_AI_MAAS/static/app.js)) for a modern web application layout.

---

## 🛠️ Tech Stack & Requirements

Dependencies are specified in [requirements.txt](file:///Users/areebalishivji/Desktop/My_AI_MAAS/requirements.txt):
- **Python:** 3.10+
- **LLM/Embeddings:** `ollama`, `chromadb`
- **Web Framework:** `fastapi`, `uvicorn[standard]`, `websockets`
- **Automation & System:** `pyautogui`, `psutil`, `pyperclip`
- **Voice/STT/TTS:** `openai-whisper`, `TTS`, `torch` (optional, configured locally)

---

## 🚀 Setup & Installation

### 1. Clone the repository and navigate inside:
```bash
git clone https://github.com/mohammedareebalishivji/My_AI_MAAS.git
cd My_AI_MAAS
```

### 2. Set up a virtual environment (do not commit this directory):
```bash
python -m venv venv_311
source venv_311/bin/activate  # macOS/Linux
# or: .\venv_311\Scripts\activate on Windows
```

### 3. Install core dependencies:
```bash
pip install -r requirements.txt
```

### 4. Ensure Ollama is installed and running:
Make sure you have Ollama running locally and have pulled your model:
```bash
ollama run llama3  # or whichever model you configure in brain.py
```

---

## 🏃 Running JARVIS 2.0

Use the unified [start_jarvis.sh](file:///Users/areebalishivji/Desktop/My_AI_MAAS/start_jarvis.sh) script to control JARVIS:

- **Web Dashboard mode:** Starts the FastAPI server and serves the Web UI.
  ```bash
  ./start_jarvis.sh web
  ```
- **Voice Command Line mode:** Starts the interactive voice CLI loop.
  ```bash
  ./start_jarvis.sh voice
  ```
- **Both modes concurrently:**
  ```bash
  ./start_jarvis.sh both
  ```
- **Check Status:**
  ```bash
  ./start_jarvis.sh status
  ```
- **Stop JARVIS:**
  ```bash
  ./start_jarvis.sh stop
  ```

---

## ⚙️ Configuration & `.env`

You can customize JARVIS behavior by creating a local `.env` file at the root:
```env
OLLAMA_API_BASE="http://localhost:11434"
LLM_MODEL="llama3"
SYSTEM_PROMPT="You are JARVIS, a highly advanced personal AI assistant..."
```

---

## 📁 Git Guidelines

Please note that database files, logs, audio records, and dependencies are ignored. Ensure you preserve [.gitignore](file:///Users/areebalishivji/Desktop/My_AI_MAAS/.gitignore) rules:
- Avoid committing large files or directories such as `venv/`, `venv_311/`, or `data/`.
- Ensure `__pycache__/` and Python precompiled files are never pushed.
