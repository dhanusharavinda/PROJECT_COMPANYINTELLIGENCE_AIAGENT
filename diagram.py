"""
Diagram connector layer for the Nimbus agent UI.

What it does today
------------------
1. build_flow_spec(): one OpenAI call that turns the agent's grounded answer
   into a small, ordered flow (3 to 6 steps) that visualises the logic or plan.
2. render_flow_png(): draws that flow as a clean paper styled PNG with Pillow,
   so the report works end to end right now.

Where the Excalidraw MCP plugs in
---------------------------------
generate_diagram() first checks for an Excalidraw backend. If you set the env
var EXCALIDRAW_MCP_URL and implement render_via_excalidraw_mcp() (one function,
marked below), the app will use the real Excalidraw render instead of the local
one, with no other changes. See EXCALIDRAW_MCP_SETUP.md for the full guide.
"""

import os
import io
import json
import textwrap
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

# Paper palette, matched to the app
PAPER = (239, 233, 221)
CARD = (251, 249, 243)
INK = (26, 26, 23)
SOFT = (87, 84, 76)
ACCENT = (26, 26, 23)


@dataclass
class DiagramResult:
    image_png: bytes = None
    link: str = None
    spec: dict = None
    source: str = "local"      # "local" or "excalidraw"
    error: str = None


# ---------------------------------------------------------------------------
# 1. Answer -> flow spec (one OpenAI call)
# ---------------------------------------------------------------------------
FLOW_SYSTEM = (
    "You convert a grounded business answer into a small, clear flow diagram spec. "
    "Read the question and the answer, then express the core logic as an ordered "
    "sequence of 3 to 6 steps. A step can be a cause, a finding, a decision, or a "
    "recommended action, whatever best captures the answer's reasoning or plan. "
    "Ground the steps in the answer; do not invent facts. "
    "Return ONLY a JSON object: "
    '{"title": "short title (max 6 words)", '
    '"steps": [{"label": "short step (max 7 words)", "detail": "one short sentence"}]}'
)


def build_flow_spec(question: str, answer: str) -> dict:
    """Ask the model for a compact, ordered flow grounded in the answer."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    user = (
        f"Question:\n{question}\n\n"
        f"Grounded answer:\n{answer}\n\n"
        "Produce the flow spec now as JSON."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": FLOW_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    data = json.loads(resp.choices[0].message.content)

    steps = []
    for s in data.get("steps", []) or []:
        label = str(s.get("label", "")).strip()
        if not label:
            continue
        steps.append({"label": label, "detail": str(s.get("detail", "")).strip()})
    if not steps:
        steps = [{"label": "See answer", "detail": "The answer did not map to a stepwise flow."}]

    return {"title": str(data.get("title", "") or "Reasoning flow").strip(), "steps": steps[:6]}


# ---------------------------------------------------------------------------
# 2. Local renderer (Pillow). Clean paper styled vertical flow.
# ---------------------------------------------------------------------------
def _font(size, bold=False, semibold=False):
    candidates = (
        ["C:/Windows/Fonts/seguisb.ttf"] if semibold else
        (["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold else
         ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"])
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    if not text:
        return []
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_flow_png(spec: dict) -> bytes:
    """Render the flow spec to a paper styled PNG and return the bytes."""
    S = 2  # supersample for crisp text
    W = 900 * S
    margin = 70 * S
    box_w = W - 2 * margin
    inner = box_w - 64 * S
    gap = 34 * S
    radius = 16 * S

    title_font = _font(30 * S, semibold=True)
    label_font = _font(21 * S, semibold=True)
    detail_font = _font(15 * S, bold=False)
    badge_font = _font(15 * S, bold=True)

    measure_img = Image.new("RGB", (10, 10))
    md = ImageDraw.Draw(measure_img)

    label_lh = 27 * S
    detail_lh = 21 * S
    pad = 18 * S

    # Measure pass
    boxes = []
    for step in spec["steps"]:
        label_lines = _wrap(md, step["label"], label_font, inner)
        detail_lines = _wrap(md, step.get("detail", ""), detail_font, inner)
        h = pad + len(label_lines) * label_lh
        if detail_lines:
            h += 6 * S + len(detail_lines) * detail_lh
        h += pad
        boxes.append((label_lines, detail_lines, int(h)))

    top = 120 * S  # room for the title
    total_h = top + sum(h for _, _, h in boxes) + gap * (len(boxes) - 1) + 50 * S

    img = Image.new("RGB", (W, total_h), PAPER)
    draw = ImageDraw.Draw(img)

    # Title and accent rule
    draw.text((margin, 44 * S), spec.get("title", "Reasoning flow"), font=title_font, fill=INK)
    draw.rectangle([margin, 92 * S, margin + 90 * S, 96 * S], fill=ACCENT)

    y = top
    x = margin
    centers = []
    for idx, (label_lines, detail_lines, h) in enumerate(boxes, start=1):
        # Hard offset shadow
        off = 5 * S
        draw.rounded_rectangle([x + off, y + off, x + box_w + off, y + h + off],
                               radius=radius, fill=INK)
        # Card
        draw.rounded_rectangle([x, y, x + box_w, y + h], radius=radius, fill=CARD,
                               outline=INK, width=2 * S)

        # Number badge
        bx, by, br = x + 26 * S, y + 24 * S, 13 * S
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=INK)
        num = str(idx)
        nb = draw.textbbox((0, 0), num, font=badge_font)
        draw.text((bx - (nb[2] - nb[0]) / 2, by - (nb[3] - nb[1]) / 2 - nb[1]),
                  num, font=badge_font, fill=CARD)

        tx = x + 54 * S
        ty = y + pad
        for ln in label_lines:
            draw.text((tx, ty), ln, font=label_font, fill=INK)
            ty += label_lh
        if detail_lines:
            ty += 6 * S
            for ln in detail_lines:
                draw.text((tx, ty), ln, font=detail_font, fill=SOFT)
                ty += detail_lh

        centers.append((x + box_w // 2, y, y + h))
        y += h + gap

    # Arrows between consecutive boxes
    for i in range(len(centers) - 1):
        cx, _, bottom = centers[i]
        _, ntop, _ = centers[i + 1]
        draw.line([cx, bottom + 4 * S, cx, ntop - 4 * S], fill=INK, width=3 * S)
        ah = 7 * S
        draw.polygon([(cx - ah, ntop - 4 * S - ah), (cx + ah, ntop - 4 * S - ah),
                      (cx, ntop - 2 * S)], fill=INK)

    # Downscale for smooth anti-aliasing
    out = img.resize((W // S, total_h // S), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 3. Excalidraw MCP integration
#
# Configure ONE of these in .env, then the app uses your real Excalidraw board:
#   EXCALIDRAW_MCP_COMMAND=npx           (+ EXCALIDRAW_MCP_ARGS=-y some-excalidraw-mcp)   # local stdio server
#   EXCALIDRAW_MCP_URL=http://host/mcp   (+ EXCALIDRAW_MCP_TOKEN=...)                      # http server
# Tool names differ between servers, so we discover them at runtime and match
# the common ones. See EXCALIDRAW_MCP_SETUP.md if your server uses other names.
# ---------------------------------------------------------------------------
def _excalidraw_configured() -> bool:
    return bool(os.getenv("EXCALIDRAW_MCP_URL") or os.getenv("EXCALIDRAW_MCP_COMMAND"))


def _pick_tool(names, candidates):
    lowered = {n.lower(): n for n in names}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    for n in names:
        if any(c in n.lower() for c in candidates):
            return n
    return None


def _spec_to_excalidraw_elements(spec):
    """Build a vertical flow as Excalidraw elements for the official MCP server.

    Format follows mcp.excalidraw.com schema: leading cameraUpdate, labeled
    rectangles, arrows with startBinding/endBinding.
    """
    x, w, h, gap = 200, 360, 90, 60
    n = len(spec["steps"])
    total_h = 120 + n * h + (n - 1) * gap + 60
    cam_h = max(600, total_h)
    elements = [{"type": "cameraUpdate", "width": 800, "height": cam_h, "x": 0, "y": 0}]

    prev_id = None
    for i, step in enumerate(spec["steps"]):
        y = 120 + i * (h + gap)
        rect_id = f"b{i}"
        text_id = f"t{i}"
        text = step["label"]
        if step.get("detail"):
            text += "\n" + step["detail"]
        # Rectangle with both `label` (for MCP create_view renderer) AND
        # boundElements (for native Excalidraw export). containerId on the
        # text element makes excalidraw.com auto-center it inside the box.
        elements.append({
            "type": "rectangle", "id": rect_id, "x": x, "y": y,
            "width": w, "height": h, "roundness": {"type": 3},
            "backgroundColor": "#a5d8ff" if i == 0 else "#b2f2bb" if i == n - 1 else "#fff3bf",
            "fillStyle": "solid", "strokeColor": "#1e1e1e",
            "label": {"text": text, "fontSize": 18},
            "boundElements": [{"type": "text", "id": text_id}],
        })
        elements.append({
            "type": "text", "id": text_id,
            "x": x + 20, "y": y + h / 2 - 12,
            "width": w - 40, "height": 24,
            "text": text, "fontSize": 18,
            "textAlign": "center", "verticalAlign": "middle",
            "containerId": rect_id,
        })
        if prev_id is not None:
            elements.append({
                "type": "arrow", "id": f"a{i}",
                "x": x + w / 2, "y": y - gap, "width": 0, "height": gap,
                "points": [[0, 0], [0, gap]], "endArrowhead": "arrow",
                "strokeColor": "#1e1e1e",
                "startBinding": {"elementId": prev_id, "fixedPoint": [0.5, 1]},
                "endBinding": {"elementId": rect_id, "fixedPoint": [0.5, 0]},
            })
        prev_id = rect_id
    return elements


def _png_from_result(result):
    """Extract PNG bytes from an MCP tool result (image blob or base64 text)."""
    import base64
    for item in getattr(result, "content", []) or []:
        data = getattr(item, "data", None)
        if data:
            try:
                return base64.b64decode(data)
            except Exception:
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
        text = getattr(item, "text", None)
        if text and len(text) > 100:
            try:
                cleaned = text.split(",")[-1].strip()
                return base64.b64decode(cleaned)
            except Exception:
                continue
    return None


def _url_from_result(result):
    """Extract the first http(s) URL from an MCP tool's text content."""
    import re
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            m = re.search(r"https?://[^\s\"'<>]+", text)
            if m:
                return m.group(0)
    return None


EXCALIDRAW_SYSTEM = """You are an expert Excalidraw diagram designer. Generate a RICH, DETAILED Excalidraw diagram grounded in the provided business answer. Use the schema below faithfully.

OUTPUT: Return ONLY a JSON object {"elements": [...]}. No prose.

REQUIRED first element:
{"type":"cameraUpdate","width":1200,"height":900,"x":0,"y":0}
(Use 1200x900 for detailed diagrams. Always 4:3 ratio.)

ELEMENTS (z-order = array order, back to front):
- Rectangle: {"type":"rectangle","id":"...","x":n,"y":n,"width":n,"height":n,"roundness":{"type":3},"backgroundColor":"#hex","fillStyle":"solid","strokeColor":"#hex","label":{"text":"...","fontSize":18}}
- Ellipse, Diamond: same shape, type changes
- Arrow: {"type":"arrow","id":"...","x":n,"y":n,"width":dx,"height":dy,"points":[[0,0],[dx,dy]],"endArrowhead":"arrow","strokeColor":"#1e1e1e","startBinding":{"elementId":"id","fixedPoint":[0.5,1]},"endBinding":{"elementId":"id","fixedPoint":[0.5,0]},"label":{"text":"short","fontSize":14}}
  fixedPoint: top=[0.5,0], bottom=[0.5,1], left=[0,0.5], right=[1,0.5]
- Standalone text (titles only): {"type":"text","id":"...","x":n,"y":n,"text":"...","fontSize":24,"strokeColor":"#1e1e1e"}
- Background zone: large translucent rectangle with opacity:30, drawn BEFORE shapes it contains

PALETTE (use consistently):
- Pastel fills: Blue #a5d8ff, Green #b2f2bb, Orange #ffd8a8, Purple #d0bfff, Red #ffc9c9, Yellow #fff3bf, Teal #c3fae8, Pink #eebefa
- Zone tints (opacity 30): UI/frontend #dbe4ff, Logic/agent #e5dbff, Data #d3f9d8
- Strokes (matching dark): #4a9eed, #22c55e, #f59e0b, #8b5cf6, #ef4444

DESIGN RULES:
- Title at top using a standalone text element (fontSize 24+, center x ≈ 600 - 8*len(title))
- Group related nodes inside translucent zones with a zone label text
- Use arrows with labels to explain transitions ("triggers", "leads to", "if churn>5%")
- Use diamond for decision points
- 8-15 elements minimum for a detailed diagram (not counting cameraUpdate)
- Minimum shape size: 140x70. Minimum 30px gap. fontSize ≥16 for body, ≥20 for headings.
- Use multiple lanes/columns when the answer has parallel concerns (causes vs effects, problem vs solution)

GROUND IT: Every box must reference a SPECIFIC fact, metric, ticket, or recommendation from the answer. No generic placeholders."""


def _build_rich_excalidraw(question: str, answer: str, spec: dict) -> list | None:
    """Ask the LLM to produce a detailed Excalidraw element list."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        user = (
            f"Question: {question}\n\n"
            f"Grounded answer:\n{answer}\n\n"
            f"Suggested flow (for inspiration, not a constraint):\n"
            f"{json.dumps(spec, indent=2)}\n\n"
            "Produce a detailed Excalidraw diagram JSON now."
        )
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXCALIDRAW_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        els = data.get("elements") or []
        if not els or not isinstance(els, list):
            return None
        if not any(e.get("type") == "cameraUpdate" for e in els):
            els.insert(0, {"type": "cameraUpdate", "width": 1200, "height": 900, "x": 0, "y": 0})
        return els
    except Exception as exc:
        print("[excalidraw] rich generation failed:", exc)
        return None


async def _excalidraw_drive(session, spec, rich_elements=None):
    import asyncio as _asyncio
    await session.initialize()
    tools = [t.name for t in (await session.list_tools()).tools]
    print("[excalidraw] available tools:", tools)

    elements = rich_elements if rich_elements else _spec_to_excalidraw_elements(spec)
    elements_str = json.dumps(elements)

    # We skip create_view: it streams elements one-by-one with animations and
    # can take minutes for rich diagrams. export_to_excalidraw is stateless —
    # it builds a shareable URL from the JSON we hand it in a single call.
    export = _pick_tool(tools, [
        "export_to_excalidraw", "export_to_png", "export_png",
        "export_image", "export_to_image", "render_png", "to_png",
    ])

    png, link = None, None
    if export:
        for args in (
            {"json": json.dumps({"elements": elements})},
            {"elements": elements_str},
            {},
        ):
            try:
                res = await _asyncio.wait_for(
                    session.call_tool(export, args), timeout=30
                )
                png = _png_from_result(res)
                link = _url_from_result(res)
                if png or link:
                    break
            except _asyncio.TimeoutError:
                print(f"[excalidraw] export timed out (args keys={list(args)})")
                continue
            except Exception as exc:
                print(f"[excalidraw] export failed (args keys={list(args)}):", exc)
                continue

    return DiagramResult(image_png=png, link=link, spec=spec, source="excalidraw")


def render_via_excalidraw_mcp(spec: dict, rich_elements=None) -> DiagramResult:
    """Render the flow on a real Excalidraw board via the configured MCP server."""
    import asyncio
    from mcp import ClientSession

    async def _run():
        if os.getenv("EXCALIDRAW_MCP_COMMAND"):
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(
                command=os.environ["EXCALIDRAW_MCP_COMMAND"],
                args=[a for a in os.getenv("EXCALIDRAW_MCP_ARGS", "").split(" ") if a],
            )
            async with stdio_client(params) as (r, w):
                async with ClientSession(r, w) as session:
                    return await _excalidraw_drive(session, spec, rich_elements)
        else:
            from mcp.client.streamable_http import streamablehttp_client
            headers = {}
            token = os.getenv("EXCALIDRAW_MCP_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            async with streamablehttp_client(os.environ["EXCALIDRAW_MCP_URL"], headers=headers) as (r, w, _):
                async with ClientSession(r, w) as session:
                    return await _excalidraw_drive(session, spec, rich_elements)

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 4. Public entry point used by the app
# ---------------------------------------------------------------------------
def generate_diagram(question: str, answer: str) -> DiagramResult:
    """Build the flow spec, then render it (Excalidraw MCP if configured, else local)."""
    spec = build_flow_spec(question, answer)

    if _excalidraw_configured():
        try:
            rich = _build_rich_excalidraw(question, answer, spec)
            result = render_via_excalidraw_mcp(spec, rich_elements=rich)
            if result and result.image_png:
                return result
            # Hosted Excalidraw MCP returns a shareable URL but no PNG bytes.
            # Pair it with the local PNG so the report has both an embedded
            # image and a clickable "open in Excalidraw" link.
            if result and result.link:
                return DiagramResult(
                    image_png=render_flow_png(spec),
                    link=result.link,
                    spec=spec,
                    source="excalidraw",
                )
            print("[excalidraw] no image returned, falling back to local renderer")
        except Exception as exc:
            print("[excalidraw] connection failed, falling back to local renderer:", exc)

    return DiagramResult(image_png=render_flow_png(spec), spec=spec, source="local")
