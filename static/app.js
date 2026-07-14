/* ============================================================
   J.A.R.V.I.S — STARK INDUSTRIES HUD CLIENT
   ============================================================ */

(() => {
    'use strict';

    const $ = id => document.getElementById(id);
    const messagesContainer = $('messagesContainer');
    const messagesWrapper = $('messagesWrapper');
    const messageInput = $('messageInput');
    const sendBtn = $('sendBtn');
    const newChatBtn = $('newChatBtn');
    const uploadBtn = $('uploadBtn');
    const fileInput = $('fileInput');
    const attachBtn = $('attachBtn');
    const welcomeScreen = $('welcomeScreen');
    const skillsList = $('skillsList');
    const skillCount = $('skillCount');
    const conversationsList = $('conversationsList');
    const ragCount = $('ragCount');
    const ragFill = $('ragFill');
    const sidebar = $('sidebar');
    const sidebarToggle = $('sidebarToggle');
    const sidebarOverlay = $('sidebarOverlay');
    const toastContainer = $('toastContainer');
    const modelName = $('modelName');
    const statusDot = $('statusDot');
    const headerStatus = $('headerStatus');
    const scrollBottomBtn = $('scrollBottomBtn');
    const dropOverlay = $('dropOverlay');
    const clearChatBtn = $('clearChatBtn');
    const themeToggle = $('themeToggle');
    const micBtn = $('micBtn');
    const voiceToggle = $('voiceToggle');
    const voiceStatus = $('voiceStatus');
    const voiceStatusLabel = $('voiceStatusLabel');
    const voiceTranscript = $('voiceTranscript');
    const voiceStopBtn = $('voiceStopBtn');
    const bootOverlay = $('bootOverlay');

    let ws = null;
    let isStreaming = false;
    let currentMessageEl = null;
    let currentContentEl = null;
    let isUserScrolled = false;
    let messageCount = 0;
    let voiceMode = localStorage.getItem('jarvis-voice') === 'true';
    let isRecording = false;
    let recognition = null;
    let currentAudio = null;
    let ttsAvailable = false;

    // ============================================================
    // BOOT SEQUENCE
    // ============================================================
    function runBootSequence() {
        setTimeout(() => {
            if (bootOverlay) bootOverlay.classList.add('hidden');
            messageInput.focus();
        }, 1500);
    }

    // ============================================================
    // PARTICLE SYSTEM — Lightweight GPU-style particles
    // ============================================================
    function initParticles() {
        const canvas = $('particleCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let particles = [];
        let w, h, raf;

        function resize() {
            w = canvas.width = window.innerWidth;
            h = canvas.height = window.innerHeight;
        }
        resize();

        let resizeTimer;
        window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 150); });

        const COUNT = 15;
        for (let i = 0; i < COUNT; i++) {
            particles.push({
                x: Math.random() * w,
                y: Math.random() * h,
                r: Math.random() * 1.5 + 0.3,
                vx: (Math.random() - 0.5) * 0.25,
                vy: (Math.random() - 0.5) * 0.15 - 0.08,
                a: Math.random() * 0.3 + 0.05,
                p: Math.random() * 6.28,
                ps: Math.random() * 0.015 + 0.003
            });
        }

        function frame() {
            ctx.clearRect(0, 0, w, h);
            for (let i = 0; i < COUNT; i++) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.p += p.ps;
                if (p.x < -5 || p.x > w + 5 || p.y < -5 || p.y > h + 5) {
                    p.x = Math.random() * w;
                    p.y = h + 3;
                }
                const alpha = p.a * (0.6 + 0.4 * Math.sin(p.p));
                ctx.globalAlpha = alpha;
                ctx.fillStyle = '#00d4ff';
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, 6.28);
                ctx.fill();
            }
            ctx.globalAlpha = 1;
            raf = requestAnimationFrame(frame);
        }
        frame();

        // Pause when hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) { cancelAnimationFrame(raf); }
            else { frame(); }
        });
    }

    // ============================================================
    // MARKDOWN CONFIG
    // ============================================================
    marked.setOptions({
        highlight: (code, lang) => {
            if (lang && hljs.getLanguage(lang)) return hljs.highlight(code, { language: lang }).value;
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });

    // ============================================================
    // WEBSOCKET
    // ============================================================
    let wsReconnectTimer = null;
    function connectWS() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        setStatus('connecting');
        ws = new WebSocket(`${proto}//${location.host}/ws/chat`);
        ws.onopen = () => { setStatus('online'); };
        ws.onmessage = e => handleMessage(JSON.parse(e.data));
        ws.onclose = () => {
            setStatus('offline');
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            wsReconnectTimer = setTimeout(connectWS, 2000);
        };
        ws.onerror = () => {};
    }

    function setStatus(state) {
        statusDot.className = 'status-dot ' + (state === 'online' ? 'online' : state === 'connecting' ? 'connecting' : '');
        const labels = { online: 'SYSTEMS ONLINE', connecting: 'INITIALIZING...', offline: 'OFFLINE' };
        modelName.textContent = labels[state] || state;
        headerStatus.textContent = state === 'online' ? 'ALL SYSTEMS NOMINAL' : labels[state];

        // Update HUD data
        const hudSec = $('hudSec');
        if (hudSec) {
            hudSec.textContent = state === 'online' ? 'LOCKED' : 'OPEN';
            hudSec.style.color = state === 'online' ? 'var(--success)' : 'var(--error)';
        }
    }

    function handleMessage(data) {
        switch (data.type) {
            case 'thinking': showThinking(); break;
            case 'skill': showSkillBadge(data.skill); break;
            case 'token': hideThinking(); appendToken(data.content); break;
            case 'tool_result': break;
            case 'done': hideThinking(); finishMessage(data.content); break;
            case 'error': hideThinking(); showError(data.content); finishMessage(); break;
            case 'audio': playServerAudio(data.content); break;
            case 'audio_fallback': playBrowserTTS(data.content); break;
        }
    }

    // ============================================================
    // MESSAGES
    // ============================================================
    function showThinking() {
        if (!currentMessageEl) currentMessageEl = createMessageEl('assistant');
        if (currentMessageEl.querySelector('.thinking-indicator')) return;
        const ind = document.createElement('div');
        ind.className = 'thinking-indicator';
        ind.innerHTML = '<div class="thinking-dots"><span></span><span></span><span></span></div><span class="thinking-label">PROCESSING...</span>';
        currentMessageEl.querySelector('.message-body').appendChild(ind);
        scrollToBottom();
    }

    function hideThinking() {
        if (!currentMessageEl) return;
        const ind = currentMessageEl.querySelector('.thinking-indicator');
        if (ind) ind.remove();
    }

    function showSkillBadge(name) {
        if (!currentMessageEl) currentMessageEl = createMessageEl('assistant');
        const badge = document.createElement('div');
        badge.className = 'skill-badge';
        badge.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> ${name.toUpperCase()}`;
        currentMessageEl.querySelector('.message-body').appendChild(badge);
        scrollToBottom();
    }

    let renderQueued = false;
    function appendToken(token) {
        if (!currentContentEl) currentContentEl = currentMessageEl.querySelector('.message-content');
        currentContentEl.dataset.raw = (currentContentEl.dataset.raw || '') + token;
        if (!renderQueued) {
            renderQueued = true;
            requestAnimationFrame(() => {
                renderContent();
                renderQueued = false;
                if (!isUserScrolled) scrollToBottom();
            });
        }
    }

    function renderContent() {
        const raw = currentContentEl.dataset.raw || '';
        const cleaned = raw.replace(/\[TOOL:.*?\]/g, '').trim();
        if (!cleaned) return;
        currentContentEl.innerHTML = marked.parse(cleaned);
        processCodeBlocks(currentContentEl);
        currentContentEl.classList.add('streaming-cursor');
    }

    function finishMessage(finalContent) {
        if (currentContentEl) {
            currentContentEl.classList.remove('streaming-cursor');
            if (finalContent) {
                const cleaned = finalContent.replace(/\[TOOL:.*?\]/g, '').trim();
                if (cleaned) currentContentEl.innerHTML = marked.parse(cleaned);
            }
            processCodeBlocks(currentContentEl);
        }
        if (currentMessageEl && currentContentEl) {
            const actions = document.createElement('div');
            actions.className = 'message-actions';
            actions.innerHTML = `<button class="msg-action" onclick="window._copyMsg(this)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy</button>`;
            currentMessageEl.querySelector('.message-body').appendChild(actions);
        }
        currentMessageEl = null;
        currentContentEl = null;
        isStreaming = false;
        updateSendButton();
        headerStatus.textContent = 'ALL SYSTEMS NOMINAL';
    }

    function showError(msg) {
        if (!currentContentEl) currentContentEl = currentMessageEl.querySelector('.message-body');
        const err = document.createElement('div');
        err.className = 'message-error';
        err.textContent = msg;
        currentContentEl.appendChild(err);
    }

    function createMessageEl(role, text) {
        if (welcomeScreen) welcomeScreen.style.display = 'none';
        messageCount++;

        const msg = document.createElement('div');
        msg.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'M' : 'J';

        const body = document.createElement('div');
        body.className = 'message-body';

        if (role === 'user' && text) {
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            bubble.textContent = text;
            body.appendChild(bubble);
        }

        if (role === 'assistant') {
            const content = document.createElement('div');
            content.className = 'message-content';
            body.appendChild(content);
        }

        msg.appendChild(avatar);
        msg.appendChild(body);
        messagesContainer.appendChild(msg);
        return msg;
    }

    // ============================================================
    // CODE BLOCKS
    // ============================================================
    function processCodeBlocks(container) {
        container.querySelectorAll('pre > code').forEach(codeEl => {
            if (codeEl.parentElement.querySelector('.code-header')) return;
            const pre = codeEl.parentElement;
            const lang = (codeEl.className.match(/language-(\w+)/) || [])[1] || 'code';
            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `<span>${lang}</span><button class="copy-btn" onclick="window._copyCode(this)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy</button>`;
            pre.insertBefore(header, codeEl);
        });
    }

    window._copyCode = function(btn) {
        const code = btn.closest('pre').querySelector('code');
        navigator.clipboard.writeText(code.textContent).then(() => {
            btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> COPIED';
            btn.classList.add('copied');
            setTimeout(() => { btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy'; btn.classList.remove('copied'); }, 2000);
        });
    };

    window._copyMsg = function(btn) {
        const content = btn.closest('.message-body').querySelector('.message-content');
        if (content) {
            navigator.clipboard.writeText(content.textContent).then(() => {
                btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> COPIED';
                setTimeout(() => { btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy'; }, 2000);
            });
        }
    };

    // ============================================================
    // SCROLL — debounced
    // ============================================================
    let scrollTicking = false;
    messagesWrapper.addEventListener('scroll', () => {
        if (scrollTicking) return;
        scrollTicking = true;
        requestAnimationFrame(() => {
            const el = messagesWrapper;
            const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
            isUserScrolled = !atBottom;
            scrollBottomBtn.hidden = atBottom;
            scrollTicking = false;
        });
    }, { passive: true });

    scrollBottomBtn.addEventListener('click', () => {
        messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
        isUserScrolled = false;
    });

    function scrollToBottom() {
        if (!isUserScrolled) {
            messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
        }
    }

    // ============================================================
    // SEND MESSAGE
    // ============================================================
    function sendMessage(text) {
        if (!text || !text.trim() || isStreaming) return;
        const msg = text.trim();
        messageInput.value = '';
        autoResize();
        updateSendButton();

        createMessageEl('user', msg);
        scrollToBottom();
        isUserScrolled = false;

        isStreaming = true;
        currentMessageEl = createMessageEl('assistant');
        currentContentEl = currentMessageEl.querySelector('.message-content');
        headerStatus.textContent = 'THINKING...';

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message: msg, voice: voiceMode }));
        }
    }

    // ============================================================
    // INPUT — debounced resize
    // ============================================================
    let resizeRAF;
    function autoResize() {
        cancelAnimationFrame(resizeRAF);
        resizeRAF = requestAnimationFrame(() => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 180) + 'px';
        });
    }

    function updateSendButton() {
        sendBtn.disabled = !messageInput.value.trim() || isStreaming;
    }

    let inputTimer;
    messageInput.addEventListener('input', () => {
        clearTimeout(inputTimer);
        inputTimer = setTimeout(() => { autoResize(); updateSendButton(); }, 30);
    }, { passive: true });
    messageInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(messageInput.value); }
    });

    document.addEventListener('keydown', e => {
        if (e.key === '/' && document.activeElement !== messageInput && !e.ctrlKey && !e.metaKey) {
            e.preventDefault(); messageInput.focus();
        }
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
            e.preventDefault(); newSession();
        }
    });

    sendBtn.addEventListener('click', () => sendMessage(messageInput.value));
    attachBtn.addEventListener('click', () => fileInput.click());

    // ============================================================
    // VOICE INPUT
    // ============================================================
    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            micBtn.title = 'Speech recognition not supported';
            micBtn.style.opacity = '0.3';
            micBtn.style.cursor = 'not-allowed';
            return null;
        }
        const rec = new SpeechRecognition();
        rec.continuous = false;
        rec.interimResults = true;
        rec.lang = 'en-US';
        rec.maxAlternatives = 1;

        rec.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            voiceStatus.hidden = false;
            voiceStatusLabel.textContent = 'LISTENING...';
            voiceTranscript.textContent = '';
        };

        rec.onresult = (event) => {
            let interim = '', final = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) final += transcript;
                else interim += transcript;
            }
            voiceTranscript.textContent = final || interim;
            if (final) voiceStatusLabel.textContent = 'HEARD:';
        };

        rec.onend = () => {
            isRecording = false;
            micBtn.classList.remove('recording');
            const transcript = voiceTranscript.textContent.trim();
            if (transcript) {
                voiceStatusLabel.textContent = 'SENDING...';
                setTimeout(() => { voiceStatus.hidden = true; }, 600);
                sendMessage(transcript);
            } else {
                voiceStatus.hidden = true;
            }
        };

        rec.onerror = (event) => {
            console.warn('[Voice] Error:', event.error);
            isRecording = false;
            micBtn.classList.remove('recording');
            voiceStatus.hidden = true;
            if (event.error === 'not-allowed') {
                showToast('Microphone access denied.', 'error');
            } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
                showToast('Voice input failed: ' + event.error, 'error');
            }
        };

        return rec;
    }

    recognition = initSpeechRecognition();

    function toggleRecording() {
        if (!recognition) { showToast('Speech recognition not available', 'error'); return; }
        if (isStreaming) return;
        if (isRecording) { recognition.stop(); }
        else {
            if (currentAudio) { currentAudio.pause(); currentAudio = null; }
            try { recognition.start(); }
            catch (e) { recognition.stop(); setTimeout(() => recognition.start(), 100); }
        }
    }

    micBtn.addEventListener('click', toggleRecording);
    voiceStopBtn.addEventListener('click', () => {
        if (isRecording && recognition) recognition.stop();
        if (currentAudio) { currentAudio.pause(); currentAudio = null; }
        voiceStatus.hidden = true;
    });

    // ============================================================
    // VOICE OUTPUT
    // ============================================================
    function playServerAudio(base64Wav) {
        if (!voiceMode) return;
        if (currentAudio) { currentAudio.pause(); }
        try {
            const bytes = Uint8Array.from(atob(base64Wav), c => c.charCodeAt(0));
            const blob = new Blob([bytes], { type: 'audio/wav' });
            const url = URL.createObjectURL(blob);
            currentAudio = new Audio(url);
            currentAudio.onended = () => { URL.revokeObjectURL(url); currentAudio = null; };
            currentAudio.onerror = () => { URL.revokeObjectURL(url); currentAudio = null; };
            currentAudio.play().catch(() => {});
        } catch (e) { console.warn('[Voice] Playback failed:', e); }
    }

    function playBrowserTTS(text) {
        if (!voiceMode || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 0.85;
        utterance.lang = 'en-US';
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(v => v.name.includes('Daniel') || v.name.includes('Google UK English Male'));
        if (preferred) utterance.voice = preferred;
        else {
            const male = voices.find(v => v.name.includes('Male') || v.name.includes('Alex'));
            if (male) utterance.voice = male;
        }
        window.speechSynthesis.speak(utterance);
    }

    function updateVoiceToggle() {
        voiceToggle.classList.toggle('active', voiceMode);
        voiceToggle.title = voiceMode ? 'Voice responses ON' : 'Voice responses OFF';
    }

    voiceToggle.addEventListener('click', () => {
        voiceMode = !voiceMode;
        localStorage.setItem('jarvis-voice', voiceMode);
        updateVoiceToggle();
        showToast(voiceMode ? 'Voice responses enabled' : 'Voice responses disabled', 'info');
    });

    updateVoiceToggle();

    async function checkTTS() {
        try {
            const res = await fetch('/api/tts/status');
            const data = await res.json();
            ttsAvailable = data.available;
        } catch {}
    }

    if (window.speechSynthesis) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }

    // ============================================================
    // FILE UPLOAD & DRAG-DROP
    // ============================================================
    fileInput.addEventListener('change', e => {
        Array.from(e.target.files).forEach(f => uploadFile(f));
        fileInput.value = '';
    });

    let dragCounter = 0;
    document.addEventListener('dragenter', e => { e.preventDefault(); dragCounter++; dropOverlay.classList.add('active'); }, { passive: true });
    document.addEventListener('dragleave', e => { e.preventDefault(); dragCounter--; if (dragCounter <= 0) { dropOverlay.classList.remove('active'); dragCounter = 0; } }, { passive: true });
    document.addEventListener('dragover', e => e.preventDefault(), { passive: true });
    document.addEventListener('drop', e => {
        e.preventDefault(); dragCounter = 0; dropOverlay.classList.remove('active');
        Array.from(e.dataTransfer.files).forEach(f => uploadFile(f));
    });

    async function uploadFile(file) {
        const form = new FormData();
        form.append('file', file);
        try {
            showToast(`Uploading ${file.name}...`, 'info');
            const res = await fetch('/api/upload', { method: 'POST', body: form });
            const data = await res.json();
            showToast(data.message, data.status === 'ok' ? 'success' : 'error');
            loadRagStats();
        } catch { showToast('Upload failed', 'error'); }
    }

    // ============================================================
    // SIDEBAR
    // ============================================================
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    sidebarOverlay.addEventListener('click', () => sidebar.classList.remove('open'));

    document.querySelectorAll('.section-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = $(btn.dataset.target);
            if (target) { target.classList.toggle('hidden'); btn.classList.toggle('collapsed'); }
        });
    });

    // ============================================================
    // SESSION
    // ============================================================
    async function newSession() {
        try {
            await fetch('/api/new-session', { method: 'POST' });
            messagesContainer.innerHTML = '';
            if (welcomeScreen) { messagesContainer.appendChild(welcomeScreen); welcomeScreen.style.display = ''; }
            currentMessageEl = null; currentContentEl = null; isStreaming = false;
            messageCount = 0; isUserScrolled = false;
            if (ws && ws.readyState === WebSocket.OPEN) ws.close();
            connectWS();
            showToast('New session initialized', 'info');
        } catch { showToast('Failed to start new session', 'error'); }
    }

    newChatBtn.addEventListener('click', newSession);
    clearChatBtn.addEventListener('click', () => {
        if (messageCount > 0 && !confirm('Initialize new session?')) return;
        newSession();
    });

    // ============================================================
    // DATA LOADING
    // ============================================================
    async function loadSkills() {
        try {
            const res = await fetch('/api/skills');
            const skills = await res.json();
            skillCount.textContent = skills.length;
            skillsList.innerHTML = skills.map(s => `<span class="skill-tag" title="${s.description}">${s.name}</span>`).join('');
        } catch {}
    }

    async function loadConversations() {
        try {
            const res = await fetch('/api/conversations');
            const convs = await res.json();
            conversationsList.innerHTML = convs.length
                ? convs.map(c => `<div class="conv-item" data-id="${c.id}">${c.title || 'Session ' + c.id}</div>`).join('')
                : '<div class="empty-state">No sessions recorded</div>';
        } catch {}
    }

    async function loadRagStats() {
        try {
            const res = await fetch('/api/rag/stats');
            const s = await res.json();
            ragCount.textContent = s.knowledge_chunks;
            ragFill.style.width = Math.min(100, s.knowledge_chunks * 5) + '%';
        } catch {}
    }

    async function loadHealth() {
        try {
            const res = await fetch('/api/health');
            const d = await res.json();
            modelName.textContent = d.model || 'Ollama';
            setStatus('online');
        } catch { setStatus('offline'); }
    }

    // ============================================================
    // TOAST
    // ============================================================
    function showToast(msg, type = 'info') {
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.textContent = msg;
        toastContainer.appendChild(t);
        setTimeout(() => t.remove(), 2500);
    }

    // ============================================================
    // QUICK ACTIONS
    // ============================================================
    document.querySelectorAll('.quick-action').forEach(btn => {
        btn.addEventListener('click', () => sendMessage(btn.dataset.msg));
    });

    // ============================================================
    // THEME
    // ============================================================
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light');
        const isLight = document.body.classList.contains('light');
        localStorage.setItem('jarvis-theme', isLight ? 'light' : 'dark');
    });

    (function loadTheme() {
        if (localStorage.getItem('jarvis-theme') === 'light') document.body.classList.add('light');
    })();

    // ============================================================
    // INIT
    // ============================================================
    runBootSequence();
    initParticles();
    connectWS();
    loadSkills();
    loadConversations();
    loadRagStats();
    loadHealth();
    checkTTS();

})();
