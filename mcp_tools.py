import os
import asyncio
from dotenv import load_dotenv
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

load_dotenv()
HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
GENIE_SPACE_ID = os.environ["GENIE_SPACE_ID"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

GENIE_URL = f"{HOST}/api/2.0/mcp/genie/{GENIE_SPACE_ID}"
VS_URL = f"{HOST}/api/2.0/mcp/vector-search/nimbus/silver"


async def _list_tools(server_url):
    async with streamablehttp_client(server_url, headers=HEADERS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [(t.name, t.description, t.inputSchema) for t in tools.tools]


def discover_tools():
    print("=== GENIE MCP TOOLS ===")
    for name, desc, schema in asyncio.run(_list_tools(GENIE_URL)):
        print(f"\nTool: {name}")
        print(f"Description: {desc}")
        print(f"Input schema: {schema}")

    print("\n\n=== VECTOR SEARCH MCP TOOLS ===")
    for name, desc, schema in asyncio.run(_list_tools(VS_URL)):
        print(f"\nTool: {name}")
        print(f"Description: {desc}")
        print(f"Input schema: {schema}")


if __name__ == "__main__":
    discover_tools()