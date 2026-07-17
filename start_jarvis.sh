#!/bin/bash
# ============================================================
#  JARVIS 2.0 — Startup Script
#  Usage: ./start_jarvis.sh [web|voice|both|stop|status|help]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

export TOKENIZERS_PARALLELISM=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

PID_FILE="data/.jarvis.pid"
LOG_FILE="data/jarvis.log"

# ---- Helpers ----

banner() {
    echo ""
    echo -e "${BLUE}         .     ${RESET}"
    echo -e "${BLUE}        .:     ${RESET}"
    echo -e "${BLUE}       .:::.   ${RESET}"
    echo -e "${BLUE}      .:::::.  ${RESET}  ${BOLD}JARVIS 2.0${RESET}"
    echo -e "${BLUE}     .::::::.  ${RESET}  ${DIM}Personal AI Assistant${RESET}"
    echo -e "${BLUE}    ::::::::::. ${RESET}"
    echo -e "${BLUE}   :::::::::::  ${RESET}"
    echo -e "${BLUE}   ::::::::::.  ${RESET}"
    echo -e "${BLUE}    '::::::::.  ${RESET}"
    echo -e "${BLUE}      '::::::   ${RESET}"
    echo -e "${BLUE}        '::::   ${RESET}"
    echo -e "${BLUE}         ':.    ${RESET}"
    echo ""
}

log()  { echo -e "${GREEN}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
err()  { echo -e "${RED}[✗]${RESET} $1"; }
info() { echo -e "${CYAN}[i]${RESET} $1"; }

check_ollama() {
    if pgrep -x "ollama" > /dev/null 2>&1; then
        log "Ollama is running"
        return 0
    fi

    warn "Ollama is not running. Starting..."
    if command -v ollama &> /dev/null; then
        ollama serve &> /dev/null &
        sleep 3
        if pgrep -x "ollama" > /dev/null 2>&1; then
            log "Ollama started"
            return 0
        fi
    fi
    err "Ollama not found. Install: https://ollama.ai"
    return 1
}

check_model() {
    local model="${OLLAMA_MODEL:-qwen2.5:7b}"
    local list_out
    list_out=$(ollama list 2>/dev/null || true)
    if echo "$list_out" | grep -q "$model"; then
        log "Model '$model' found"
    else
        warn "Model '$model' not pulled yet"
        info "Run: ollama pull $model"
        info "Continuing anyway"
    fi
}

setup_venv() {
    if [ -d "venv_311" ]; then
        source venv_311/bin/activate
        log "Virtual environment: venv_311"
    elif [ -d "venv" ]; then
        source venv/bin/activate
        log "Virtual environment: venv"
    else
        warn "No venv found — using system Python"
    fi
    export COQUI_TOS_AGREED=1
}

check_deps() {
    local missing=()
    python3 -c "import fastapi" 2>/dev/null || missing+=("fastapi")
    python3 -c "import uvicorn" 2>/dev/null || missing+=("uvicorn")
    python3 -c "import ollama" 2>/dev/null || missing+=("ollama")
    python3 -c "import chromadb" 2>/dev/null || missing+=("chromadb")
    python3 -c "import speech_recognition" 2>/dev/null || missing+=("SpeechRecognition")
    python3 -c "import whisper" 2>/dev/null || missing+=("openai-whisper")
    python3 -c "import pyaudio" 2>/dev/null || missing+=("pyaudio")

    if [ ${#missing[@]} -gt 0 ]; then
        warn "Missing packages: ${missing[*]}"
        info "Installing..."
        pip install "${missing[@]}" -q 2>/dev/null
        log "Dependencies installed"
    fi
}

check_port() {
    local port="${1:-8000}"
    if lsof -i :"$port" -sTCP:LISTEN &>/dev/null; then
        err "Port $port is already in use"
        info "Stop the other process or use: ./start_jarvis.sh stop"
        return 1
    fi
    return 0
}

ensure_data_dirs() {
    mkdir -p data/uploads
}

cleanup() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            log "Stopped JARVIS (PID $pid)"
        fi
        rm -f "$PID_FILE"
    fi
}

# ---- Commands ----

cmd_web() {
    banner
    ensure_data_dirs
    check_ollama || exit 1
    check_model
    setup_venv
    check_deps
    check_port 8000 || exit 1

    echo ""
    info "Starting web interface..."
    echo -e "  ${BOLD}Open: http://localhost:8000${RESET}"
    echo -e "  ${DIM}Press Ctrl+C to stop${RESET}"
    echo ""

    python server.py 2>&1 | tee -a "$LOG_FILE" &
    echo $! > "$PID_FILE"

    # Auto-open browser after 2 seconds (macOS only)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        (sleep 2 && open "http://localhost:8000") &
    fi

    wait
}

cmd_voice() {
    banner
    ensure_data_dirs
    check_ollama || exit 1
    check_model
    setup_venv
    check_deps

    echo ""
    info "Starting voice mode..."
    echo -e "  ${DIM}Speak to interact. Say 'exit' to quit.${RESET}"
    echo -e "  ${DIM}Uses local Whisper for speech recognition.${RESET}"
    echo ""

    # Check if microphone is available (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! python3 -c "import speech_recognition; sr = speech_recognition.Recognizer(); sr.Microphone()" 2>/dev/null; then
            err "No microphone detected. Please connect a mic."
            exit 1
        fi
        info "Microphone OK"
    fi

    python main.py
}

cmd_both() {
    banner
    ensure_data_dirs
    check_ollama || exit 1
    check_model
    setup_venv
    check_deps
    check_port 8000 || exit 1

    echo ""
    info "Starting full mode (Web + Voice)..."
    echo -e "  ${BOLD}Web: http://localhost:8000${RESET}"
    echo -e "  ${DIM}Voice: Active${RESET}"
    echo ""

    python server.py &> /dev/null &
    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"
    sleep 2

    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:8000"
    fi

    python main.py
    kill "$SERVER_PID" 2>/dev/null
    rm -f "$PID_FILE"
}

cmd_stop() {
    if [ -f "$PID_FILE" ]; then
        cleanup
    else
        # Try to find and kill any running server
        local pid
        pid=$(lsof -ti :8000 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null
            log "Stopped process on port 8000 (PID $pid)"
        else
            warn "No JARVIS process found"
        fi
    fi
}

cmd_status() {
    echo ""
    info "JARVIS Status"
    echo -e "  ${DIM}─────────────────────────────${RESET}"

    # Ollama
    if pgrep -x "ollama" > /dev/null 2>&1; then
        echo -e "  Ollama:      ${GREEN}Running${RESET}"
    else
        echo -e "  Ollama:      ${RED}Not running${RESET}"
    fi

    # Server
    if lsof -i :8000 -sTCP:LISTEN &>/dev/null; then
        echo -e "  Web Server:  ${GREEN}Running${RESET} (port 8000)"
    else
        echo -e "  Web Server:  ${RED}Not running${RESET}"
    fi

    # Model
    local model="${OLLAMA_MODEL:-qwen2.5:7b}"
    local list_out
    list_out=$(ollama list 2>/dev/null || true)
    if echo "$list_out" | grep -q "$model"; then
        echo -e "  Model:        ${GREEN}$model${RESET}"
    else
        echo -e "  Model:        ${YELLOW}$model (not pulled)${RESET}"
    fi

    # Voice (Whisper)
    if python3 -c "import whisper" 2>/dev/null; then
        echo -e "  Whisper STT: ${GREEN}Available${RESET}"
    else
        echo -e "  Whisper STT: ${YELLOW}Not installed${RESET}"
    fi

    # Microphone
    if python3 -c "import speech_recognition; sr = speech_recognition.Recognizer(); sr.Microphone()" 2>/dev/null; then
        echo -e "  Microphone:  ${GREEN}Detected${RESET}"
    else
        echo -e "  Microphone:  ${YELLOW}Not detected${RESET}"
    fi

    # Venv
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        echo -e "  Python:      ${GREEN}$(python3 --version 2>&1)${RESET} (${VIRTUAL_ENV##*/})"
    else
        echo -e "  Python:      ${YELLOW}$(python3 --version 2>&1)${RESET} (system)"
    fi

    # Data
    local chunks
    chunks=$(python3 -c "from memory.rag_engine import RAGEngine; print(RAGEngine().get_stats()['knowledge_chunks'])" 2>/dev/null || echo "0")
    echo -e "  Knowledge:   ${CYAN}${chunks}${RESET} chunks indexed"

    echo -e "  ${DIM}─────────────────────────────${RESET}"
    echo ""
}

cmd_help() {
    banner
    echo -e "${BOLD}Usage:${RESET}"
    echo "  ./start_jarvis.sh [command]"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo -e "  ${CYAN}web${RESET}      Start web interface (default)"
    echo -e "  ${CYAN}voice${RESET}    Start voice mode (local Whisper STT)"
    echo -e "  ${CYAN}listen${RESET}   Alias for voice mode"
    echo -e "  ${CYAN}both${RESET}     Start web + voice simultaneously"
    echo -e "  ${CYAN}stop${RESET}     Stop all JARVIS processes"
    echo -e "  ${CYAN}status${RESET}   Show system status"
    echo -e "  ${CYAN}help${RESET}     Show this help"
    echo ""
    echo -e "${BOLD}Examples:${RESET}"
    echo "  ./start_jarvis.sh              # Start web UI"
    echo "  ./start_jarvis.sh web          # Same as above"
    echo "  ./start_jarvis.sh voice        # Voice mode only"
    echo "  ./start_jarvis.sh both         # Everything"
    echo "  ./start_jarvis.sh stop         # Kill all"
    echo "  ./start_jarvis.sh status       # Check what's running"
    echo ""
    echo -e "${DIM}Web interface opens at: http://localhost:8000${RESET}"
    echo -e "${DIM}Voice mode uses local Whisper (tiny) for speech-to-text${RESET}"
    echo ""
}

# ---- Main ----

trap cleanup EXIT

MODE="${1:-web}"

case "$MODE" in
    web|server)  cmd_web   ;;
    voice|listen|mic) cmd_voice ;;
    both)        cmd_both  ;;
    stop|kill)   cmd_stop  ;;
    status)      cmd_status ;;
    help|--help|-h) cmd_help ;;
    *)
        err "Unknown command: $MODE"
        echo ""
        cmd_help
        exit 1
        ;;
esac
