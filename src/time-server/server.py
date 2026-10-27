import asyncio
import uvicorn
from datetime import datetime
from starlette.applications import Starlette
from starlette.routing import Mount
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

mcp = FastMCP("time-server")

@mcp.tool()
def get_current_time() -> str:
    """Returns the current UTC time."""
    return datetime.utcnow().isoformat()

async def run_server():
    session_manager = StreamableHTTPSessionManager(app=mcp)
    async def handle_streamable_http(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)
    app = Starlette(routes=[Mount("/mcp", app=handle_streamable_http)])
    config = uvicorn.Config(app, host="0.0.0.0", port=80, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_server())