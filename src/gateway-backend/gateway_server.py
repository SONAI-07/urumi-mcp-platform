import asyncio
import contextvars
import logging
import httpx
import uvicorn
import os
import time
from datetime import datetime
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from database import SessionLocal
from models import MCPServer, AuditLog
from auth import authenticate_raw_key

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("urumi-gateway")

current_user = contextvars.ContextVar("current_user", default="anonymous")

class MCPAuthMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            headers = dict(scope["headers"])
            auth = headers.get(b"authorization", b"").decode()
            raw = auth.split(" ")[1] if auth.startswith("Bearer ") else ""
            username = authenticate_raw_key(raw)
            if username is None:
                await JSONResponse({"detail": "Invalid gateway key"}, status_code=401)(scope, receive, send)
                return
            current_user.set(username)
        await self.app(scope, receive, send)

def log_audit(server, tool, success, duration_ms):
    db = SessionLocal()
    try:
        db.add(AuditLog(username=current_user.get(), server_name=server, tool_name=tool,
                        success=success, duration_ms=duration_ms, timestamp=datetime.utcnow()))
        db.commit()
    finally: db.close()

@mcp.tool()
async def gateway_ping() -> str:
    return "pong from gateway"

async def run_server():
    session_manager = StreamableHTTPSessionManager(app=mcp)
    async def handle(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)
    app = Starlette(routes=[Mount("/mcp", app=handle)])
    app.add_middleware(MCPAuthMiddleware)
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
    await uvicorn.Server(config).serve()

if __name__ == "__main__":
    asyncio.run(run_server())