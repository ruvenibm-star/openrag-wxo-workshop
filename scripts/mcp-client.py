#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.12,<2"]
# ///
"""Connect to OpenRAG's MCP server (<OPENRAG_URL>/mcp, streamable HTTP) the way an agent does, list its
tools, and call them.

Authentication follows the watsonx.data docs: x-username plus x-api-key, where x-api-key holds the
password, or a Software Hub API key with x-username ibmlhapikey_<username>. --auth basic sends an HTTP
Basic header instead, which is what a watsonx Orchestrate basic connection sends.

    scripts/mcp-client.py tools                         names and descriptions
    scripts/mcp-client.py tools --schema                with input schemas
    scripts/mcp-client.py call openrag_search '{"query": "propulsion pod torque", "limit": 3}'
    scripts/mcp-client.py smoke                         the Lab 3 checks

Settings come from the environment, then from secrets/secrets.env one level above the workshop folder,
if it exists: OPENRAG_URL, OPENRAG_USERNAME (default CPD_USERNAME), and OPENRAG_API_KEY or
OPENRAG_PASSWORD (default CPD_PASSWORD).
"""

import argparse
import asyncio
import base64
import json
import os
import re
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

REPO = Path(__file__).resolve().parent.parent.parent


def settings():
    env = {}
    secrets = REPO / "secrets" / "secrets.env"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
            if m:
                env[m[1]] = m[2].strip().strip('"').strip("'")
    get = lambda *keys: next((v for k in keys for v in (os.environ.get(k), env.get(k)) if v), None)
    url = get("OPENRAG_URL")
    user = get("OPENRAG_USERNAME", "CPD_USERNAME")
    secret = get("OPENRAG_API_KEY", "OPENRAG_PASSWORD", "CPD_PASSWORD")
    if not (url and user and secret):
        sys.exit("Set OPENRAG_URL, OPENRAG_USERNAME and OPENRAG_PASSWORD or OPENRAG_API_KEY")
    return url.rstrip("/") + "/mcp", user, secret


def headers(auth, user, secret):
    if auth == "basic":
        return {"Authorization": "Basic " + base64.b64encode(f"{user}:{secret}".encode()).decode()}
    return {"x-username": user, "x-api-key": secret}


def text_of(result):
    return "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")


async def run(args):
    url, user, secret = settings()
    async with streamablehttp_client(url, headers=headers(args.auth, user, secret)) as (read, write, _):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"Connected to {info.serverInfo.name} {info.serverInfo.version} at {url} as {user} ({args.auth})\n")
            if args.cmd == "tools":
                for tool in (await session.list_tools()).tools:
                    print(f"{tool.name}\n    {' '.join((tool.description or '').split())[:160]}")
                    if args.schema:
                        print("    " + json.dumps(tool.inputSchema.get("properties", {})))
            elif args.cmd == "call":
                result = await session.call_tool(args.tool, json.loads(args.arguments))
                print(text_of(result))
            elif args.cmd == "smoke":
                await smoke(session)


async def smoke(session):
    tools = {t.name for t in (await session.list_tools()).tools}
    print(f"{len(tools)} tools: {', '.join(sorted(tools))}\n")

    filters = json.loads(text_of(await session.call_tool("openrag_search_knowledge_filters", {"query": "Current policies"})))
    match = [f for f in filters.get("filters", filters if isinstance(filters, list) else []) if f.get("name") == "Current policies"]
    filter_id = match[0]["id"] if match else None
    print(f"openrag_search_knowledge_filters: Current policies -> {filter_id}\n")

    hits = json.loads(text_of(await session.call_tool("openrag_search", {"query": "propulsion pod mounting bolt torque", "limit": 3})))
    print("openrag_search: propulsion pod mounting bolt torque")
    for hit in hits.get("results", []):
        print(f"    {hit.get('score', 0):6.2f}  {hit.get('filename')}")

    args = {"message": "How long is a SECRET security clearance valid?"}
    if filter_id:
        args["filter_id"] = filter_id
    chat = json.loads(text_of(await session.call_tool("openrag_chat", args)))
    answer = re.sub(r"\(Source: [^)]+\)", "", chat.get("response", "")).strip()
    print(f"\nopenrag_chat with filter_id: {args['message']}\n    {answer}")
    if chat.get("chat_id"):
        await session.call_tool("openrag_delete_chat", {"chat_id": chat["chat_id"]})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--auth", choices=["headers", "basic"], default="headers")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("tools"); s.add_argument("--schema", action="store_true")
    s = sub.add_parser("call"); s.add_argument("tool"); s.add_argument("arguments", nargs="?", default="{}")
    sub.add_parser("smoke")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
