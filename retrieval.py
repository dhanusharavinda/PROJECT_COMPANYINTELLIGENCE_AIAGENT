import os
import asyncio
import json
import time
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

# The real tool names discovered from the MCP servers
GENIE_QUERY_TOOL = f"query_space_{GENIE_SPACE_ID}"
GENIE_POLL_TOOL = f"poll_response_{GENIE_SPACE_ID}"
TICKETS_TOOL = "nimbus__silver__tickets_index"
DOCS_TOOL = "nimbus__silver__docs_index"


def _extract_text(result):
    """Pull the text content out of an MCP tool result."""
    texts = []
    for item in result.content:
        if hasattr(item, "text"):
            texts.append(item.text)
    return "\n".join(texts)


async def _genie_query(question: str) -> str:
    """Ask Genie a question. Handles the async poll loop until complete."""
    async with streamablehttp_client(GENIE_URL, headers=HEADERS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Initial query
            result = await session.call_tool(GENIE_QUERY_TOOL, {"query": question})
            text = _extract_text(result)

            try:
                data = json.loads(text)
            except Exception:
                return text  # plain text response, nothing to poll

            # Genie uses camelCase keys: conversationId, messageId, status
            conversation_id = data.get("conversationId")
            message_id = data.get("messageId")
            status = (data.get("status") or "").upper()

            # Statuses that mean "done"
            done_states = {"COMPLETED", "COMPLETE", "SUCCEEDED", "FAILED", "ERROR"}

            # If already done, return it
            if status in done_states:
                return text

            # If we have ids, poll until done
            if conversation_id and message_id:
                for attempt in range(30):  # up to ~60 seconds
                    await asyncio.sleep(2)
                    poll = await session.call_tool(
                        GENIE_POLL_TOOL,
                        {"conversation_id": conversation_id, "message_id": message_id},
                    )
                    poll_text = _extract_text(poll)
                    try:
                        poll_data = json.loads(poll_text)
                    except Exception:
                        return poll_text
                    poll_status = (poll_data.get("status") or "").upper()
                    if poll_status in done_states:
                        return poll_text
                # ran out of polling attempts
                return poll_text

            # No ids and not done, just return what we got
            return text


async def _vector_search(tool_name: str, query: str) -> str:
    """Run a semantic search against a vector index tool."""
    async with streamablehttp_client(VS_URL, headers=HEADERS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, {"query": query})
            return _extract_text(result)


# --- Synchronous wrappers the agent will call ---

def query_genie(question: str) -> str:
    """Ask the Genie space a natural-language question. Returns text."""
    return asyncio.run(_genie_query(question))


def search_tickets(query: str) -> str:
    """Semantic search over support tickets. Returns matching ticket text."""
    return asyncio.run(_vector_search(TICKETS_TOOL, query))


def search_docs(query: str) -> str:
    """Semantic search over internal documents. Returns matching doc chunks."""
    return asyncio.run(_vector_search(DOCS_TOOL, query))


# --- Test when run directly ---
if __name__ == "__main__":
    print("=== Testing Genie ===")
    print(query_genie("How many SMB customers churned in September 2025?"))
    print("\n=== Testing ticket search ===")
    print(search_tickets("customers angry about price increase"))
    print("\n=== Testing doc search ===")
    print(search_docs("pricing strategy decision"))