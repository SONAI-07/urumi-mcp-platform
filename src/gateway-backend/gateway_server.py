import asyncio
import json
import time
import logging
import uvicorn
from mcp.server import Server
import mcp.types as types
from mcp.server.streamable_http import StreamableHTTPServer

from database import SessionLocal
from models import MCPServer, AuditLog
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logging.basicConfig(level=logging.INFO)

# We use the low-level Server to dynamically control the list_tools and call_tool handlers
app = Server("Urumi-Gateway")


def log_audit(username: str, server_name: str, tool_name: str, duration_ms: int, success: bool, error_msg: str = None):
    db = SessionLocal()
    try:
        log = AuditLog(
            username=username, server_name=server_name, tool_name=tool_name,
            duration_ms=duration_ms, success=success, error_message=error_msg
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


async def get_upstream_tools():
    """Dynamically fetches tools from all enabled upstream servers."""
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
                        # Prefix tool name to prevent collisions: "server__tool"
                        gateway_name = f"{server.name}__{tool.name}"
                        all_tools.append(types.Tool(
                            name=gateway_name,
                            description=f"[{server.name}] {tool.description or tool.name}",
                            inputSchema=tool.inputSchema
                        ))
        except Exception as e:
            logging.error(f"Failed to fetch tools from {server.name}: {e}")

    return all_tools


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return await get_upstream_tools()


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if arguments is None:
        arguments = {}

    # Parse the prefixed name: "server_name__tool_name"
    if "__" not in name:
        return [types.TextContent(type="text", text=json.dumps({"error": "Invalid tool name format"}))]

    server_name, upstream_tool_name = name.split("__", 1)

    db = SessionLocal()
    server = db.query(MCPServer).filter(MCPServer.name == server_name, MCPServer.is_enabled == True).first()
    db.close()

    if not server:
        return [
            types.TextContent(type="text", text=json.dumps({"error": f"Server {server_name} not found or disabled"}))]

    headers = {}
    if server.auth_header_name and server.auth_token_hash:
        headers[server.auth_header_name] = server.auth_token_hash

    start_time = time.time()
    try:
        # STRICT TIMEOUT: A dead upstream cannot block the gateway
        async with asyncio.timeout(10.0):
            async with streamablehttp_client(server.url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(upstream_tool_name, arguments)

        duration = int((time.time() - start_time) * 1000)
        log_audit("system", server_name, upstream_tool_name, duration, True)
        return result.content

    except asyncio.TimeoutError:
        duration = int((time.time() - start_time) * 1000)
        log_audit("system", server_name, upstream_tool_name, duration, False, "Timeout")
        return [types.TextContent(type="text", text=json.dumps({"error": "Upstream server timed out"}))]
    except Exception as e:
        duration = int((time.time() - start_time) * 1000)
        log_audit("system", server_name, upstream_tool_name, duration, False, str(e))
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    # Initialize the Streamable HTTP server wrapper
    http_server = StreamableHTTPServer(app)

    # Run via uvicorn
    config = uvicorn.Config(
        http_server.app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())