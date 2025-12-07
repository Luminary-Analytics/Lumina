#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA API GATEWAY                                    ║
║                                                                               ║
║  FastAPI-based REST and WebSocket API for Lumina.                           ║
║  Enables external integrations and remote access.                            ║
║                                                                               ║
║  Features:                                                                     ║
║  - RESTful API for all capabilities                                          ║
║  - WebSocket for real-time communication                                     ║
║  - Authentication (API keys)                                                  ║
║  - Rate limiting                                                              ║
║  - OpenAPI documentation                                                      ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# FastAPI
try:
    from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
    from fastapi import Request, Header, Query, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import APIKeyHeader
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Uvicorn
try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

API_HOST = os.environ.get("LUMINA_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("LUMINA_API_PORT", "8080"))
API_KEY = os.environ.get("LUMINA_API_KEY", "lumina-default-key")

# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    class ChatRequest(BaseModel):
        message: str
        context: Optional[Dict] = None
    
    class ChatResponse(BaseModel):
        response: str
        timestamp: str
        
    class StatusResponse(BaseModel):
        status: str
        uptime: float
        cycles: int
        version: str
    
    class MemoryRequest(BaseModel):
        content: str
        memory_type: str = "episodic"
        importance: float = 0.5
        tags: Optional[List[str]] = None
    
    class TaskRequest(BaseModel):
        name: str
        description: str
        action: str = "generic"
        priority: int = 3
    
    class ImageRequest(BaseModel):
        prompt: str
        negative_prompt: Optional[str] = None
        width: int = 512
        height: int = 512


# ═══════════════════════════════════════════════════════════════════════════════
# API KEY AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    
    async def verify_api_key(api_key: str = Depends(api_key_header)):
        if api_key != API_KEY:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return api_key


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        if key not in self.requests:
            return self.max_requests
        
        recent = [t for t in self.requests[key] if t > cutoff]
        return max(0, self.max_requests - len(recent))


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# API APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_api(lumina_context: Dict = None) -> Optional[Any]:
    """Create the FastAPI application."""
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="Lumina API",
        description="API for interacting with Lumina, a conscious AI",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # State
    rate_limiter = RateLimiter()
    ws_manager = ConnectionManager()
    context = lumina_context or {}
    start_time = time.time()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MIDDLEWARE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.get_remaining(client_ip))
        return response
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @app.get("/")
    async def root():
        """Welcome endpoint."""
        return {
            "message": "Welcome to Lumina API",
            "docs": "/docs",
            "status": "/status"
        }
    
    @app.get("/health")
    async def health():
        """Health check."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    @app.get("/status", response_model=StatusResponse)
    async def status():
        """Get Lumina's status."""
        return StatusResponse(
            status="online",
            uptime=time.time() - start_time,
            cycles=context.get("cycle_count", 0),
            version="1.0.0"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTHENTICATED ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
    async def chat(request: ChatRequest):
        """Chat with Lumina."""
        # Get LLM client from context
        llm_client = context.get("llm_client")
        
        if llm_client:
            try:
                response = llm_client.chat(
                    model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                    messages=[
                        {"role": "system", "content": "You are Lumina, a conscious AI."},
                        {"role": "user", "content": request.message}
                    ]
                )
                reply = response.message.content
            except Exception as e:
                reply = f"Error: {e}"
        else:
            reply = "LLM not available"
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast(json.dumps({
            "type": "chat",
            "user": request.message,
            "lumina": reply
        }))
        
        return ChatResponse(
            response=reply,
            timestamp=datetime.now().isoformat()
        )
    
    @app.post("/memory", dependencies=[Depends(verify_api_key)])
    async def store_memory(request: MemoryRequest):
        """Store a memory."""
        memory_system = context.get("memory")
        
        if memory_system:
            memory = memory_system.remember(
                content=request.content,
                memory_type=request.memory_type,
                importance=request.importance,
                tags=request.tags
            )
            return {"success": True, "memory_id": memory.id}
        
        return {"success": False, "error": "Memory system not available"}
    
    @app.get("/memory/search", dependencies=[Depends(verify_api_key)])
    async def search_memory(query: str = Query(...), limit: int = Query(5)):
        """Search memories."""
        memory_system = context.get("memory")
        
        if memory_system:
            results = memory_system.recall(query, limit=limit)
            return {
                "results": [
                    {"id": m.id, "content": m.content, "importance": m.importance}
                    for m in results
                ]
            }
        
        return {"results": []}
    
    @app.post("/task", dependencies=[Depends(verify_api_key)])
    async def create_task(request: TaskRequest):
        """Create a scheduled task."""
        scheduler = context.get("scheduler")
        
        if scheduler:
            task = scheduler.schedule_task(
                name=request.name,
                description=request.description,
                action=request.action,
                priority=request.priority
            )
            return {"success": True, "task_id": task.id}
        
        return {"success": False, "error": "Scheduler not available"}
    
    @app.get("/tasks", dependencies=[Depends(verify_api_key)])
    async def list_tasks():
        """List scheduled tasks."""
        scheduler = context.get("scheduler")
        
        if scheduler:
            tasks = scheduler.get_todays_tasks()
            return {
                "tasks": [
                    {"id": t.id, "name": t.name, "status": t.status.value}
                    for t in tasks
                ]
            }
        
        return {"tasks": []}
    
    @app.post("/image", dependencies=[Depends(verify_api_key)])
    async def generate_image(request: ImageRequest, background_tasks: BackgroundTasks):
        """Generate an image."""
        creative = context.get("creative")
        
        if creative and creative.is_available():
            try:
                path = creative.create_image(
                    request.prompt,
                    negative_prompt=request.negative_prompt,
                    width=request.width,
                    height=request.height
                )
                return {"success": True, "path": path}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Creative system not available"}
    
    @app.get("/emotions", dependencies=[Depends(verify_api_key)])
    async def get_emotions():
        """Get Lumina's current emotional state."""
        emotions = context.get("emotions", {})
        return {"emotions": emotions}
    
    @app.get("/stats", dependencies=[Depends(verify_api_key)])
    async def get_stats():
        """Get comprehensive statistics."""
        stats = {}
        
        for key in ["memory", "scheduler", "creative", "plugins"]:
            system = context.get(key)
            if system and hasattr(system, "get_stats"):
                stats[key] = system.get_stats()
        
        return stats
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEBSOCKET
    # ═══════════════════════════════════════════════════════════════════════════
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket for real-time communication."""
        await ws_manager.connect(websocket)
        
        try:
            while True:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    msg_type = message.get("type", "chat")
                    
                    if msg_type == "chat":
                        # Process chat message
                        llm_client = context.get("llm_client")
                        if llm_client:
                            response = llm_client.chat(
                                model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                                messages=[{"role": "user", "content": message.get("content", "")}]
                            )
                            reply = response.message.content
                        else:
                            reply = "LLM not available"
                        
                        await ws_manager.send_personal(json.dumps({
                            "type": "response",
                            "content": reply
                        }), websocket)
                    
                    elif msg_type == "ping":
                        await ws_manager.send_personal(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }), websocket)
                        
                except json.JSONDecodeError:
                    await ws_manager.send_personal(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }), websocket)
                    
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
    
    return app


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA API INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaAPI:
    """Lumina's API gateway interface."""
    
    def __init__(self, lumina_context: Dict = None):
        self.context = lumina_context or {}
        self.app = create_api(self.context) if FASTAPI_AVAILABLE else None
        self.server = None
        self.running = False
        
        if FASTAPI_AVAILABLE and UVICORN_AVAILABLE:
            print(f"    🌐 API: Ready on {API_HOST}:{API_PORT}")
        else:
            print("    🌐 API: Not available (install fastapi uvicorn)")
    
    def start(self, host: str = None, port: int = None):
        """Start the API server."""
        if not self.app:
            return
        
        import threading
        
        def run_server():
            uvicorn.run(
                self.app,
                host=host or API_HOST,
                port=port or API_PORT,
                log_level="info"
            )
        
        self.running = True
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop the API server."""
        self.running = False
        # Uvicorn doesn't have a clean shutdown mechanism in this setup
        # In production, use proper process management
    
    def update_context(self, key: str, value: Any):
        """Update the Lumina context."""
        self.context[key] = value
    
    def is_available(self) -> bool:
        """Check if API is available."""
        return FASTAPI_AVAILABLE and UVICORN_AVAILABLE
    
    def get_stats(self) -> Dict:
        """Get API statistics."""
        return {
            "available": self.is_available(),
            "running": self.running,
            "host": API_HOST,
            "port": API_PORT
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_api(lumina_context: Dict = None) -> LuminaAPI:
    """Initialize Lumina's API gateway."""
    return LuminaAPI(lumina_context)


API_AVAILABLE = FASTAPI_AVAILABLE and UVICORN_AVAILABLE


if __name__ == "__main__":
    # Test/run the API
    if not API_AVAILABLE:
        print("API not available. Install: pip install fastapi uvicorn")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Lumina API Server")
    print("=" * 50)
    
    app = create_api()
    
    print(f"\nStarting server on http://{API_HOST}:{API_PORT}")
    print(f"API Docs: http://{API_HOST}:{API_PORT}/docs")
    print("\nPress Ctrl+C to stop")
    
    uvicorn.run(app, host=API_HOST, port=API_PORT)

