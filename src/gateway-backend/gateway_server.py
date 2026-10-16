import asyncio
import contextlib
import json
import time
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
import mcp.types as types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from database import SessionLocal
from models import MCPServer, AuditLog

logging.basicConfig(level=logging.INFO)

# Low-level server: we need raw control over list_tools/call_tool
# because the gateway's tool list is DYNAMIC (comes from the DB).
app = Server("Urumi-Gateway")


def log_audit(username, server_name, tool_name, duration_ms, success, error_msg=None):
    db = SessionLocal()
    try:
        db.add(AuditLog(
            username=username, server_name=server_name, tool_name=tool_name,
            duration_ms=duration_ms, success=success, error_message=error_msg
        ))
        db.commit()
    finally:
        db.close()


async def get_upstream_tools():
    """Dynamically fetch tools from every ENABLED upstream server."""
    db = SessionLocal()
    servers = db.query(MCPServer).filter(MCPServer.is_enabled == True).all()
    db.close()

    all_tools = []
    for server in servers:
        try:
            headers = {}
            if server.auth_header_name and server.auth_token_hash:
                headers[server.auth_header_name] = server.auth_token_hash

            async with streamablehttp_client(server.url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    upstream_tools = await session.list_tools()
                    for tool in upstream_tools.tools:
                        all_tools.append(types.Tool(
                            name=f"{server.name}__{tool.name}",   # collision-proof prefix
                            description=f"[{server.name}] {tool.description or tool.name}",
                            inputSchema=tool.inputSchema,
                        ))
        except Exception as e:
            # A dead upstream must NOT break the listing of the others
            logging.error(f"Failed to fetch tools from {server.name}: {e}")
    return all_tools


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return await get_upstream_tools()


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}

    if "__" not in name:
        return [types.TextContent(type="text", text=json.dumps({"error": "Invalid tool name format"}))]

    server_name, upstream_tool = name.split("__", 1)

    db = SessionLocal()
    server = db.query(MCPServer).filter(
        MCPServer.name == server_name, MCPServer.is_enabled == True).first()
    db.close()

    if not server:
        return [types.TextContent(type="text", text=json.dumps(
            {"error": f"Server {server_name} not found or disabled"}))]

    headers = {}
    if server.auth_header_name and server.auth_token_hash:
        headers[server.auth_header_name] = server.auth_token_hash

    start = time.time()
    try:
        async with asyncio.timeout(10.0):   # dead/slow upstream cannot hang the gateway
            async with streamablehttp_client(server.url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(upstream_tool, arguments)

        duration = int((time.time() - start) * 1000)
        log_audit("system", server_name, upstream_tool, duration, True)
        return result.content

    except asyncio.TimeoutError:
        duration = int((time.time() - start) * 1000)
        log_audit("system", server_name, upstream_tool, duration, False, "Timeout")
        return [types.TextContent(type="text", text=json.dumps({"error": "Upstream server timed out"}))]
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        log_audit("system", server_name, upstream_tool, duration, False, str(e))
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ---------- HTTP wiring (the part that was wrong before) ----------
session_manager = StreamableHTTPSessionManager(app=app)


@contextlib.asynccontextmanager
async def lifespan(starlette_app: Starlette):
    async with session_manager.run():
        yield


starlette_app = Starlette(
    routes=[Mount("/mcp", app=session_manager.handle_request)],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8001)