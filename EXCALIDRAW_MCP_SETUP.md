# Connecting the Excalidraw MCP

Important truth first: the Excalidraw connector you see inside Claude or Cursor
is bound to *that* app's session. This Streamlit app is a separate Python
process, so it cannot borrow that connection. The app must talk to its own
Excalidraw MCP server. That is what this guide sets up.

The integration is already written in `diagram.py`. You only need to (1) run an
Excalidraw MCP server and (2) point the app at it with one or two env vars. When
it is connected, the Flow diagram and the report use the real Excalidraw render.
If anything fails, the app falls back to the local renderer so it never breaks.

## Step 1: Run an Excalidraw MCP server

You need a server that can create elements and export the board to PNG. Pick one
from npm or GitHub (search "excalidraw mcp"). Most run as a local stdio process
through `npx`, the same way MCP servers are launched in Claude Desktop config.

Quick sanity check that it launches:

```
npx -y <the-excalidraw-mcp-package>
```

## Step 2: Point the app at it (.env in this folder)

For a local stdio server (most common):

```
EXCALIDRAW_MCP_COMMAND=npx
EXCALIDRAW_MCP_ARGS=-y <the-excalidraw-mcp-package>
```

Or for an HTTP server:

```
EXCALIDRAW_MCP_URL=http://localhost:3000/mcp
EXCALIDRAW_MCP_TOKEN=optional-bearer-token
```

Setting either `EXCALIDRAW_MCP_COMMAND` or `EXCALIDRAW_MCP_URL` switches the app
from the local renderer to your MCP automatically. No code change needed.

## Step 3: Confirm the tool names

Servers name their tools differently. On the first run the app prints the
server's tools to the Streamlit console:

```
[excalidraw] available tools: ['create_element', 'batch_create_elements', 'export_to_png', ...]
```

`diagram.py` already matches the common names for "create elements" and "export
to PNG" (see `_pick_tool`). If your server uses different names or a different
argument shape, adjust two small functions in `diagram.py`:

- `_spec_to_excalidraw_elements(spec)`: builds the boxes + arrows. The spec is
  `{"title": str, "steps": [{"label": str, "detail": str}]}`. Map each step to
  whatever element shape your server expects.
- `_excalidraw_drive(session, spec)`: the `create` and `export` candidate lists,
  and the export argument dict.

## Step 4: Run

```
.\venv\Scripts\streamlit.exe run app.py
```

Ask a question with the Excalidraw connector on (the "+" in the composer). The
Flow diagram section and the PDF will now use your Excalidraw board, and the
caption shows a share link if your server returns one.

## Adding more connectors later

Add an entry to `CONNECTORS` in `app.py` (key, name, desc, default) and a new
toggle appears under the "+" automatically. Handle its key on the results page
the same way `result_excalidraw` is handled.
