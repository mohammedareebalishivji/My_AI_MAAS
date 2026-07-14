import os
import re
import json
import asyncio
import base64
import tempfile
import queue
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from brain import JarvisBrain
from automation import JarvisHands
from skill_engine import SkillEngine
from memory.sqlite_memory import SQLiteMemory
from memory.rag_engine import RAGEngine

app = FastAPI(title="JARVIS AI", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
base_dir = Path(__file__).parent

jarvis_brain = JarvisBrain()
jarvis_hands = JarvisHands()
skill_engine = SkillEngine()
jarvis_db = SQLiteMemory()
rag = RAGEngine()

tools_desc = jarvis_hands.get_tool_descriptions()
jarvis_brain.add_tool_descriptions(tools_desc)

active_connections = []

# ── TTS Engine (lazy-loaded) ────────────────────────────────────
_tts_engine = None
_tts_available = None  # None = not tried, True/False = tried


def _get_tts():
    global _tts_engine, _tts_available
    if _tts_available is False:
        return None
    if _tts_engine is not None:
        return _tts_engine
    try:
        from voice import JarvisVoice
        print("[TTS] Loading XTTS v2 model (first time may download ~2GB)...")
        _tts_engine = JarvisVoice()
        _tts_available = True
        print("[TTS] Ready")
        return _tts_engine
    except Exception as e:
        print(f"[TTS] Unavailable: {e}")
        _tts_available = False
        return None


def _generate_tts_audio(text):
    engine = _get_tts()
    if not engine:
        return None
    try:
        text_clean = re.sub(r'[*#`\[\]TOOL:.*?\]]', '', text).strip()
        if len(text_clean) > 2000:
            text_clean = text_clean[:2000]
        if not text_clean:
            return None
        fd, tmp_path = tempfile.mkstemp(suffix=".wav", dir="/tmp")
        os.close(fd)
        engine.tts.tts_to_file(
            text=text_clean,
            speaker=engine.speaker_name,
            language="en",
            file_path=tmp_path,
        )
        with open(tmp_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return audio_b64
    except Exception as e:
        print(f"[TTS] Generation failed: {e}")
        return None


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class TTSRequest(BaseModel):
    text: str


class IngestRequest(BaseModel):
    text: Optional[str] = None
    filepath: Optional[str] = None
    directory: Optional[str] = None


def _execute_tool_call(tool_call_str):
    tool_pattern = r"(\w+)\((.*?)\)"
    match = re.match(tool_pattern, tool_call_str.strip())
    if not match:
        return None, "Invalid tool format"

    tool_name = match.group(1)
    args_str = match.group(2).strip()

    kwargs = {}
    if args_str:
        arg_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
        for am in re.finditer(arg_pattern, args_str):
            key = am.group(1)
            value = am.group(2) or am.group(3) or am.group(4)
            kwargs[key] = value

    if not kwargs and args_str:
        clean = args_str.strip().strip('"').strip("'")
        skill = skill_engine.classify(tool_name)
        if skill and skill.parameters:
            kwargs[skill.parameters[0]] = clean

    result = jarvis_hands.execute(tool_name, **kwargs)
    return tool_name, result


def _handle_tools(response_text):
    tool_pattern = r"\[TOOL:\s*(.*?)\]"
    matches = re.findall(tool_pattern, response_text)
    results = []
    for match in matches:
        tool_name, result = _execute_tool_call(match)
        if result:
            results.append(f"Result of {tool_name}: {result}")
    return "\n".join(results) if results else None


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "").strip()

            if not user_message:
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            if user_message.lower() in ["exit", "quit", "shutdown"]:
                await websocket.send_json({"type": "done", "content": "Goodbye, sir."})
                break

            await websocket.send_json({"type": "thinking", "content": ""})

            rag_memories = rag.search_conversations(user_message, n_results=3)
            rag_context = None
            if rag_memories:
                rag_context = "\n".join([m["text"][:300] for m in rag_memories])

            skill = skill_engine.classify(user_message)
            skill_context = None
            if skill:
                params = skill_engine.extract_params(skill, user_message)
                result = jarvis_hands.execute(skill.action, **params)
                skill_context = {"name": skill.name, "result": result}
                await websocket.send_json({
                    "type": "skill",
                    "skill": skill.name,
                    "result": result[:500]
                })

            full_response = ""
            current_input = user_message
            iterations = 0

            while iterations < 3:
                iterations += 1
                chunk_buffer = ""
                q = queue.Queue()

                def _produce(q, text, rag_ctx, skill_ctx):
                    try:
                        for token in jarvis_brain.chat_stream(
                            text,
                            rag_context=rag_ctx,
                            skill_context=skill_ctx
                        ):
                            q.put(("token", token))
                    except Exception as e:
                        q.put(("error", str(e)))
                    finally:
                        q.put(("done", None))

                producer = asyncio.to_thread(
                    _produce, q, current_input,
                    rag_context if iterations == 1 else None,
                    skill_context if iterations == 1 else None
                )

                while True:
                    msg_type, data = await asyncio.to_thread(q.get)
                    if msg_type == "token":
                        chunk_buffer += data
                        await websocket.send_json({"type": "token", "content": data})
                    elif msg_type == "error":
                        await websocket.send_json({"type": "error", "content": data})
                        break
                    elif msg_type == "done":
                        break

                await producer

                tool_results = _handle_tools(chunk_buffer)
                full_response = chunk_buffer

                if tool_results:
                    current_input = (
                        f"TOOL_RESULTS: {tool_results}\n"
                        "Continue if not complete, otherwise acknowledge."
                    )
                    await websocket.send_json({
                        "type": "tool_result",
                        "content": tool_results[:1000]
                    })
                else:
                    break

            clean_final = re.sub(r"\[TOOL:.*?\]", "", full_response).strip()
            rag.store_conversation(user_message, clean_final)

            await websocket.send_json({"type": "done", "content": clean_final})

            # Generate and send TTS audio (non-blocking)
            if payload.get("voice"):
                audio_b64 = await asyncio.to_thread(_generate_tts_audio, clean_final)
                if audio_b64:
                    await websocket.send_json({"type": "audio", "content": audio_b64})
                else:
                    await websocket.send_json({"type": "audio_fallback", "content": clean_final})

    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


@app.get("/api/conversations")
async def get_conversations():
    convs = jarvis_db.get_recent_conversations(limit=50)
    return convs


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: int):
    conv = jarvis_db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.post("/api/ingest")
async def ingest_content(req: IngestRequest):
    if req.text:
        num = rag.ingest_text(req.text)
        return {"status": "ok", "chunks": num, "message": f"Ingested {num} chunks"}

    if req.filepath:
        num, msg = rag.ingest_file(req.filepath)
        return {"status": "ok", "chunks": num, "message": msg}

    if req.directory:
        num, results = rag.ingest_directory(req.directory)
        return {"status": "ok", "chunks": num, "files": results}

    raise HTTPException(status_code=400, detail="Provide text, filepath, or directory")


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    upload_dir = base_dir / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    num, msg = rag.ingest_file(str(file_path))
    return {"status": "ok", "chunks": num, "message": msg, "filename": file.filename}


@app.get("/api/rag/stats")
async def rag_stats():
    return rag.get_stats()


@app.get("/api/skills")
async def list_skills():
    return [{"name": s.name, "description": s.description, "keywords": s.keywords}
            for s in skill_engine.skills]


@app.post("/api/new-session")
async def new_session():
    jarvis_brain.clear_context()
    return {"status": "ok", "message": "New session started"}


@app.get("/api/tts/status")
async def tts_status():
    available = _get_tts() is not None
    return {"available": available, "engine": "xtts_v2" if available else None}


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    audio = await asyncio.to_thread(_generate_tts_audio, req.text)
    if audio:
        return {"status": "ok", "audio": audio, "format": "wav"}
    raise HTTPException(status_code=503, detail="TTS engine not available")


@app.get("/api/health")
async def health():
    return {"status": "online", "model": jarvis_brain.model}


app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(str(base_dir / "static" / "index.html"))


if __name__ == "__main__":
    import uvicorn
    config = uvicorn.Config(
        app, host="0.0.0.0", port=8000,
        ws_ping_timeout=300, ws_ping_interval=300
    )
    server = uvicorn.Server(config)
    server.run()
