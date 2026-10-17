"""Chat agent: Sarvam LLM (OpenAI-compatible) + MCP client to our own gateway."""
import os
import json
import logging
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger("agent")

SARVAM_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"
MODEL = os.environ.get("SARVAM_MODEL", "sarvam-m")
GATEWAY_MCP_URL = os.environ.get("GATEWAY_MCP_URL", "http://127.0.0.1:8001/mcp")
MAX_STEPS = 6

SYSTEM_PROMPT = (
    "You are the Urumi Store operations assistant. You can inspect and manage the "
    "WooCommerce store through the provided tools. Use tools whenever the user asks "
    "about products, orders or store operations, and summarise tool results in clear, "
    "friendly language."
)

def _to_openai_tools(mcp_tools):
    return [{
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description or t.name,
            "parameters": t.inputSchema or {"type": "object", "properties": {}},
        },
    } for t in mcp_tools]

async def _llm(messages, tools):
    headers = {"Authorization": f"Bearer {SARVAM_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": messages, "temperature": 0.2}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(SARVAM_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]

async def run_agent(user_message: str, history: list):
    if not SARVAM_KEY:
        return {"reply": "Agent misconfigured: SARVAM_API_KEY is missing.", "history": history}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + \
               [{"role": "user", "content": user_message}]

    async with streamablehttp_client(GATEWAY_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = _to_openai_tools(listed.tools)

            for _ in range(MAX_STEPS):
                msg = await _llm(messages, tools)
                messages.append(msg)                      # assistant turn (may carry tool_calls)
                calls = msg.get("tool_calls") or []
                if not calls:
                    reply = msg.get("content") or ""
                    return {"reply": reply,
                            "history": history + [
                                {"role": "user", "content": user_message},
                                {"role": "assistant", "content": reply}]}
                for call in calls:                        # execute each tool via MCP
                    fn = call["function"]
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        result = await session.call_tool(fn["name"], args)
                        text = "\n".join(getattr(c, "text", str(c)) for c in result.content)
                    except Exception as e:
                        text = json.dumps({"error": str(e)})
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": text})

    return {"reply": "I reached my tool-call step limit before finishing.", "history": history}