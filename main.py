import asyncio
import uuid
import time
import json
import base64
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.http import HTTPFlow

# ==========================================
# 1. State & Connection Manager
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.history: List[Dict[str, Any]] = []
        self.MAX_HISTORY = 1000

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        for event in self.history:
            await websocket.send_text(json.dumps(event))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        self.history.append(message)
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)
            
        text = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

# ==========================================
# 2. FastAPI Setup
# ==========================================
app = FastAPI(title="LLM Proxyman")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==========================================
# 3. Mitmproxy Addon
# ==========================================
class LlmInterceptor:
    def __init__(self, manager: ConnectionManager, loop: asyncio.AbstractEventLoop):
        self.manager = manager
        self.loop = loop

    def _broadcast_safe(self, message: Dict[str, Any]):
        asyncio.run_coroutine_threadsafe(self.manager.broadcast(message), self.loop)

    def _detect_client_tool(self, headers: Dict[str, str]) -> str:
        # Determine the client tool from headers
        ua = headers.get("user-agent", "").lower()
        if "codex" in ua:
            return "codex"
        elif "claude" in ua or "anthropic" in ua:
            return "claude"
        elif "opencode" in ua:
            return "opencode"
        elif "gemini" in ua or "google" in ua:
            return "gemini"
        
        # Checking custom headers just in case
        for k, v in headers.items():
            val = v.lower()
            if "codex" in val: return "codex"
            if "claude" in val: return "claude"
            if "opencode" in val: return "opencode"
            if "gemini" in val: return "gemini"
            
        return ""

    def request(self, flow: HTTPFlow):
        headers = dict(flow.request.headers)
        req_data = {
            "id": flow.id,
            "method": flow.request.method,
            "url": flow.request.url,
            "headers": headers,
            "client_tool": self._detect_client_tool(headers)
        }
        
        if flow.request.content:
            try:
                req_data["body"] = json.loads(flow.request.content)
            except Exception:
                try:
                    req_data["body"] = flow.request.content.decode('utf-8')
                except Exception:
                    req_data["body"] = "<binary payload>"

        self._broadcast_safe({"type": "request", "data": req_data, "id": flow.id})

    def response(self, flow: HTTPFlow):
        content_type = flow.response.headers.get("content-type", "").lower()
        if "text/event-stream" not in content_type:
            resp_data = {
                "id": flow.id,
                "status": flow.response.status_code,
                "headers": dict(flow.response.headers),
            }
            if flow.response.content:
                try:
                    resp_data["body"] = json.loads(flow.response.content)
                except Exception:
                    try:
                        resp_data["body"] = flow.response.content.decode('utf-8')
                    except Exception:
                        resp_data["body"] = "<binary payload>"
            self._broadcast_safe({"type": "response", "data": resp_data, "id": flow.id})

    def responseheaders(self, flow: HTTPFlow):
        content_type = flow.response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type:
            resp_data = {
                "id": flow.id,
                "status": flow.response.status_code,
                "headers": dict(flow.response.headers),
                "streaming": True
            }
            self._broadcast_safe({"type": "response", "data": resp_data, "id": flow.id})
            flow.response.stream = self.handle_stream_chunk(flow.id)
            
    def handle_stream_chunk(self, flow_id: str):
        def _stream(chunk: bytes):
            try:
                text_chunk = chunk.decode('utf-8', errors='ignore')
                self._broadcast_safe({
                    "type": "stream_chunk", 
                    "id": flow_id, 
                    "chunk": text_chunk
                })
            except Exception as e:
                pass
            return chunk
        return _stream

# ==========================================
# 4. Main Runner
# ==========================================
async def start_mitmproxy(manager: ConnectionManager, loop: asyncio.AbstractEventLoop, port: int = 10080):
    opts = options.Options(listen_host='0.0.0.0', listen_port=port)
    m = DumpMaster(opts, with_termlog=False, with_dumper=False)
    m.addons.add(LlmInterceptor(manager, loop))
    print(f"[*] Mitmproxy running on port {port}...")
    await m.run()

async def main():
    loop = asyncio.get_running_loop()
    config = uvicorn.Config(app, host="0.0.0.0", port=10011, log_level="info")
    server = uvicorn.Server(config)
    print("[*] Starting LLM Visualizer UI on http://127.0.0.1:10011")
    await asyncio.gather(
        server.serve(),
        start_mitmproxy(manager, loop, port=10080)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
