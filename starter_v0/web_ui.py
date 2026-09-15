from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
import chat

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Northstar Labs IT Helpdesk — AI Agent Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-secondary: #111827;
      --bg-card: #1a2234;
      --bg-card-hover: #222d44;
      --border-color: #2a364f;
      --text-main: #f3f4f6;
      --text-muted: #94a3b8;
      --accent-cyan: #06b6d4;
      --accent-blue: #3b82f6;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-purple: #8b5cf6;
      --code-bg: #0d131f;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: linear-gradient(180deg, rgba(17, 24, 39, 0.95) 0%, rgba(10, 14, 23, 0.8) 100%);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .logo-badge {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
    }
    .header-title h1 {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .header-title p {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .status-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-emerald);
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px var(--accent-emerald);
    }
    .header-meta {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .meta-chip {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }
    .meta-chip .label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    .meta-chip .val { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent-cyan); }
    main {
      flex: 1;
      max-width: 1100px;
      width: 100%;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      padding: 20px;
      gap: 16px;
    }
    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding-bottom: 4px;
    }
    .chip-btn {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .chip-btn:hover {
      background: var(--bg-card-hover);
      color: var(--text-main);
      border-color: var(--accent-cyan);
      transform: translateY(-1px);
    }
    .chat-container {
      flex: 1;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      min-height: 520px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .messages-pane {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .msg-row {
      display: flex;
      gap: 12px;
      max-width: 85%;
    }
    .msg-row.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .msg-row.assistant {
      align-self: flex-start;
    }
    .avatar {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 600;
      flex-shrink: 0;
    }
    .msg-row.user .avatar {
      background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
      color: #fff;
    }
    .msg-row.assistant .avatar {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald));
      color: #0a0e17;
    }
    .msg-bubble {
      padding: 14px 18px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.6;
    }
    .msg-row.user .msg-bubble {
      background: #2563eb;
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .msg-row.assistant .msg-bubble {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      border-bottom-left-radius: 4px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .msg-bubble pre {
      white-space: pre-wrap;
      word-break: break-word;
      font-family: inherit;
    }
    .tool-cards-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 4px;
    }
    .tool-card {
      background: var(--code-bg);
      border: 1px solid rgba(6, 182, 212, 0.25);
      border-radius: 10px;
      overflow: hidden;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
    }
    .tool-header {
      background: rgba(6, 182, 212, 0.08);
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(6, 182, 212, 0.15);
      cursor: pointer;
    }
    .tool-name-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tool-icon {
      color: var(--accent-cyan);
      font-weight: 700;
    }
    .tool-name {
      color: var(--accent-cyan);
      font-weight: 600;
    }
    .tool-badge {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      font-weight: 700;
    }
    .tool-badge.success { background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); }
    .tool-badge.error { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); }
    .tool-badge.waiting { background: rgba(245, 158, 11, 0.2); color: var(--accent-amber); }
    .tool-body {
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .tool-section-label {
      color: var(--text-muted);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .tool-code-block {
      background: #060910;
      border-radius: 6px;
      padding: 8px;
      overflow-x: auto;
      max-height: 220px;
      color: #cbd5e1;
      font-size: 11px;
    }
    .typing-indicator {
      display: none;
      align-items: center;
      gap: 6px;
      padding: 12px 16px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      width: fit-content;
    }
    .dot {
      width: 6px;
      height: 6px;
      background: var(--accent-cyan);
      border-radius: 50%;
      animation: pulse 1.4s infinite ease-in-out both;
    }
    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes pulse {
      0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
      40% { transform: scale(1); opacity: 1; }
    }
    .input-bar {
      padding: 16px 20px;
      background: var(--bg-card);
      border-top: 1px solid var(--border-color);
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .input-bar input {
      flex: 1;
      background: var(--code-bg);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
      font-family: inherit;
      transition: border-color 0.2s ease;
    }
    .input-bar input:focus {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.2);
    }
    .btn {
      padding: 12px 20px;
      border-radius: 10px;
      border: none;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
      color: #fff;
    }
    .btn-primary:hover {
      opacity: 0.9;
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: var(--bg-card-hover);
      color: var(--text-muted);
      border: 1px solid var(--border-color);
    }
    .btn-secondary:hover {
      color: var(--text-main);
      border-color: var(--accent-cyan);
    }
    .footer-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      font-size: 11px;
      color: var(--text-muted);
    }
    .footer-bar a { color: var(--accent-cyan); text-decoration: none; }
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <div class="logo-badge">NL</div>
      <div class="header-title">
        <h1>Northstar Labs Helpdesk <span class="status-badge"><span class="status-dot"></span> Online</span></h1>
        <p>IT Support Agent Studio with Real-Time Tool Execution & Audit Trails</p>
      </div>
    </div>
    <div class="header-meta">
      <div class="meta-chip">
        <span class="label">Artifact Version</span>
        <span class="val" id="meta-version">v3+p...</span>
      </div>
      <div class="meta-chip">
        <span class="label">Model</span>
        <span class="val" id="meta-model">gpt-4o-mini</span>
      </div>
      <button class="btn btn-secondary" onclick="exportTranscript()" style="padding: 6px 12px; font-size: 12px;">
        📥 Transcript
      </button>
      <button class="btn btn-secondary" onclick="clearChat()" style="padding: 6px 12px; font-size: 12px;">
        🗑️ Clear
      </button>
    </div>
  </header>

  <main>
    <div class="quick-chips">
      <button class="chip-btn" onclick="sendPrompt(this.innerText)">Dịch vụ VPN ở môi trường production hiện tại có ổn định không?</button>
      <button class="chip-btn" onclick="sendPrompt(this.innerText)">Kiểm tra kết nối mạng trên laptop của mình giúp với.</button>
      <button class="chip-btn" onclick="sendPrompt(this.innerText)">Kiểm tra thời hạn bảo hành phần cứng và gói dịch vụ của máy LT-204.</button>
      <button class="chip-btn" onclick="sendPrompt(this.innerText)">Kiểm tra song song phần cứng và mạng trên máy DT-031.</button>
      <button class="chip-btn" onclick="sendPrompt(this.innerText)">Tạo ticket mức high cho sự cố mạng LAN tầng 4.</button>
    </div>

    <div class="chat-container">
      <div class="messages-pane" id="messages-pane">
        <div class="msg-row assistant">
          <div class="avatar">🤖</div>
          <div class="msg-bubble">
            <pre>Xin chào! Tôi là trợ lý IT Helpdesk của Northstar Labs. Tôi có thể hỗ trợ bạn chẩn đoán sự cố thiết bị, kiểm tra tình trạng dịch vụ, tra cứu thời hạn bảo hành phần cứng, tra cứu cẩm nang kỹ thuật hoặc tạo ticket hỗ trợ. Bạn cần giúp gì hôm nay?</pre>
          </div>
        </div>
      </div>

      <div class="typing-indicator" id="typing-indicator" style="margin: 0 24px 12px 24px;">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
        <span style="font-size: 12px; color: var(--text-muted); margin-left: 6px;">Agent đang phân tích & định tuyến công cụ...</span>
      </div>

      <div class="input-bar">
        <input type="text" id="user-input" placeholder="Nhập yêu cầu hỗ trợ IT hoặc chọn câu hỏi mẫu phía trên..." onkeydown="if(event.key==='Enter') sendMessage()">
        <button class="btn btn-primary" id="send-btn" onclick="sendMessage()">Gửi yêu cầu ⚡</button>
      </div>
    </div>

    <div class="footer-bar">
      <span>Được xây dựng theo quy chuẩn Lab 04 — Base v3 100% | Group 100% | Adversarial 91.67%</span>
      <span id="transcript-status">Transcript: Auto-saving</span>
    </div>
  </main>

  <script>
    let chatHistory = [];
    let currentTranscriptId = null;

    async function loadMeta() {
      try {
        const res = await fetch('/api/info');
        const data = await res.json();
        document.getElementById('meta-version').innerText = data.artifact_version;
        document.getElementById('meta-model').innerText = data.model;
        currentTranscriptId = data.transcript_id;
      } catch (e) {
        console.error('Failed to load info', e);
      }
    }

    function renderToolCard(event) {
      const isErr = event.result && event.result.error;
      const isClarify = event.result && event.result.awaiting_user;
      let badgeClass = 'success';
      let badgeText = 'SUCCESS';
      if (isErr) { badgeClass = 'error'; badgeText = 'ERROR'; }
      else if (isClarify) { badgeClass = 'waiting'; badgeText = 'AWAITING USER'; }

      const jsonArgs = JSON.stringify(event.args, null, 2);
      const jsonRes = JSON.stringify(event.result, null, 2);

      return `
        <div class="tool-card">
          <div class="tool-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'flex' : 'none'">
            <div class="tool-name-wrap">
              <span class="tool-icon">⚡</span>
              <span class="tool-name">${event.tool}</span>
            </div>
            <span class="tool-badge ${badgeClass}">${badgeText}</span>
          </div>
          <div class="tool-body">
            <div>
              <div class="tool-section-label">Input Arguments</div>
              <div class="tool-code-block">${jsonArgs}</div>
            </div>
            <div>
              <div class="tool-section-label">Tool Execution Result</div>
              <div class="tool-code-block">${jsonRes}</div>
            </div>
          </div>
        </div>
      `;
    }

    function parseAssistantReply(text) {
      try {
        const obj = JSON.parse(text);
        if (obj && obj.reply) return obj.reply;
      } catch (e) {}
      return text;
    }

    function appendMessage(role, text, toolEvents = []) {
      const pane = document.getElementById('messages-pane');
      const row = document.createElement('div');
      row.className = `msg-row ${role}`;
      const avatar = document.createElement('div');
      avatar.className = 'avatar';
      avatar.innerText = role === 'user' ? '👤' : '🤖';

      const bubble = document.createElement('div');
      bubble.className = 'msg-bubble';

      if (toolEvents && toolEvents.length > 0) {
        const toolContainer = document.createElement('div');
        toolContainer.className = 'tool-cards-container';
        toolContainer.innerHTML = toolEvents.map(renderToolCard).join('');
        bubble.appendChild(toolContainer);
      }

      const pre = document.createElement('pre');
      pre.innerText = role === 'assistant' ? parseAssistantReply(text) : text;
      bubble.appendChild(pre);

      row.appendChild(avatar);
      row.appendChild(bubble);
      pane.appendChild(row);
      pane.scrollTop = pane.scrollHeight;
    }

    async function sendMessage() {
      const input = document.getElementById('user-input');
      const text = input.value.trim();
      if (!text) return;

      appendMessage('user', text);
      input.value = '';
      input.disabled = true;
      document.getElementById('send-btn').disabled = true;
      document.getElementById('typing-indicator').style.display = 'flex';

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history: chatHistory })
        });
        const data = await res.json();
        document.getElementById('typing-indicator').style.display = 'none';

        appendMessage('assistant', data.assistant_text || 'Đã thực thi yêu cầu.', data.tool_events || []);
        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: data.assistant_text || '' });
        if (data.transcript_id) {
          currentTranscriptId = data.transcript_id;
          document.getElementById('transcript-status').innerText = `Transcript: ${data.transcript_id}`;
        }
      } catch (err) {
        document.getElementById('typing-indicator').style.display = 'none';
        appendMessage('assistant', `Lỗi kết nối: ${err.message}`, []);
      } finally {
        input.disabled = false;
        document.getElementById('send-btn').disabled = false;
        input.focus();
      }
    }

    function sendPrompt(text) {
      document.getElementById('user-input').value = text;
      sendMessage();
    }

    function clearChat() {
      document.getElementById('messages-pane').innerHTML = `
        <div class="msg-row assistant">
          <div class="avatar">🤖</div>
          <div class="msg-bubble">
            <pre>Hội thoại đã được làm mới. Mời bạn nhập yêu cầu mới!</pre>
          </div>
        </div>
      `;
      chatHistory = [];
    }

    async function exportTranscript() {
      if (!currentTranscriptId) {
        alert('Chưa có transcript nào được ghi trong phiên này.');
        return;
      }
      window.open(`/api/transcript/${currentTranscriptId}`, '_blank');
    }

    loadMeta();
  </script>
</body>
</html>
"""


class AgentWebHandler(BaseHTTPRequestHandler):
    agent_state: dict[str, Any] = {}

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default noisy console logs

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path == "/api/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            info = {
                "artifact_version": self.agent_state["artifact_version"].artifact_version,
                "version": self.agent_state["version"],
                "provider": self.agent_state["provider_name"],
                "model": self.agent_state["model"],
                "transcript_id": self.agent_state["transcript_id"],
                "tools": [t["name"] for t in self.agent_state["tools"]],
            }
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
            return

        if self.path.startswith("/api/transcript/"):
            tid = self.path.split("/api/transcript/")[-1]
            tfile = TRANSCRIPTS_DIR / f"{safe_slug(tid)}.transcript.json"
            if tfile.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename={tfile.name}")
                self.end_headers()
                self.wfile.write(tfile.read_bytes())
                return
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            payload = json.loads(body)
            user_msg = payload.get("message", "").strip()
            history = payload.get("history", [])

            system_prompt = self.agent_state["system_prompt"]
            tools = self.agent_state["openai_tools"]
            provider = self.agent_state["provider"]
            model = self.agent_state["model"]

            messages = [
                {"role": "system", "content": system_prompt},
                *chat.trim_history(history, 5),
                {"role": "user", "content": user_msg},
            ]

            turn_record: dict[str, Any] = {
                "turn_index": len(self.agent_state["transcript"]["turns"]) + 1,
                "started_at": now_iso(),
                "user": user_msg,
                "status": "started",
                "assistant_text": None,
                "rounds": [],
                "tool_events": [],
            }

            try:
                result = chat.run_model_tool_loop(
                    provider=provider,
                    messages=messages,
                    tools=tools,
                    model=model,
                    max_tool_rounds=4,
                )
                turn_record.update(result)
            except Exception as exc:
                turn_record.update({
                    "status": "provider_error",
                    "error": f"{type(exc).__name__}: {str(exc)}",
                    "assistant_text": f"Lỗi thực thi: {str(exc)}",
                })

            turn_record["ended_at"] = now_iso()
            self.agent_state["transcript"]["turns"].append(turn_record)
            chat.write_transcript(self.agent_state["transcript_path"], self.agent_state["transcript"]["transcript"])

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            out = {
                "assistant_text": turn_record.get("assistant_text") or "",
                "status": turn_record.get("status"),
                "tool_events": turn_record.get("tool_events", []),
                "transcript_id": self.agent_state["transcript_id"],
            }
            self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_web_server(port: int = 7860, version: str = "v3", provider_name: str = "openrouter") -> None:
    system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)
    selected_model = getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(version, ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"{safe_slug(version)}_{safe_slug(provider_name)}_{timestamp}"
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"

    transcript_data = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": selected_model,
        "system_prompt": str(ARTIFACTS_DIR / "system_prompt.md"),
        "tools": str(ARTIFACTS_DIR / "tools.yaml"),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    AgentWebHandler.agent_state = {
        "system_prompt": system_prompt,
        "tools": tool_declarations,
        "openai_tools": openai_tools,
        "provider": provider,
        "provider_name": provider_name,
        "model": selected_model,
        "version": version,
        "artifact_version": artifact_version,
        "transcript_id": transcript_id,
        "transcript_path": transcript_path,
        "transcript": {"transcript": transcript_data, "turns": transcript_data["turns"]},
    }

    server_address = ("", port)
    httpd = HTTPServer(server_address, AgentWebHandler)
    print("=" * 60)
    print(f"🚀 Northstar Labs IT Helpdesk Web UI running at:")
    print(f"   👉 http://localhost:{port}")
    print(f"   Artifact Version: {artifact_version.artifact_version}")
    print(f"   Provider: {provider_name} | Model: {selected_model}")
    print(f"   Transcript File: {transcript_path.name}")
    print("=" * 60)
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb UI stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web UI for Northstar Labs IT Helpdesk Agent.")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--version", default="v3")
    parser.add_argument("--provider", default="openrouter")
    args = parser.parse_args()
    run_web_server(port=args.port, version=args.version, provider_name=args.provider)
