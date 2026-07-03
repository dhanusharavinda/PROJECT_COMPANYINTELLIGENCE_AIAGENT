"""
Nimbus Analytics: Company Intelligence AI Agent
A multipage Streamlit interface for the existing LangGraph self-correcting agent.

This file is a thin UI layer. It does not modify the agent. It imports
build_agent() from agent.py and invokes it exactly as documented.

Pages:
  ask      -> the composer (question, preloaded context, attachments, connectors)
  insights -> runs the agent and shows the answer, the flow diagram, the report
"""

import os
import io
import json
import uuid
import datetime

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from diagram import generate_diagram

load_dotenv()

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Nimbus Analytics: Company Intelligence AI Agent",
    page_icon="https://www.svgrepo.com/show/530439/ai-technology.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEMO_QUESTIONS = [
    "Why did SMB churn spike in Q3 2025?",
    "What happened with the dashboard in December 2025?",
    "How can we reduce SMB churn without lowering prices?",
    "Based on the docs I uploaded, help me increase the revenue and retention of the company",
    "List all the things you can do",
]

CONNECTORS = [
    {"key": "excalidraw", "name": "Excalidraw", "default": True},
]

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
PRELOADED_PDF_PATH = os.path.join(ASSET_DIR, "business_context.pdf")
PRELOADED_PDF_NAME = "Nimbus Analytics Business Context and Current Problems.pdf"

# ---------------------------------------------------------------------------
# Styling: paper, minimal, retro, with a premium italic serif headline.
# ---------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@1,9..144,400;1,9..144,600&family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

:root {
    --paper: #efe9dd;
    --card: #fbf9f3;
    --ink: #1a1a17;
    --ink-soft: #57544c;
    --line: #1a1a17;
    --shadow: 4px 4px 0 #1a1a17;
    --shadow-lg: 6px 6px 0 #1a1a17;
}

.stApp { background-color: var(--paper); color: var(--ink); font-family: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif; }
.stApp::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: 0.06;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 960px; position: relative; z-index: 1; }

/* Full-width header bar, flush to the top and edge to edge */
.topbar {
    display: flex; justify-content: space-between; align-items: center;
    width: 100vw; position: relative; left: 50%; margin-left: -50vw;
    border: none; border-bottom: 2px solid var(--line); border-radius: 0;
    background: var(--card); box-shadow: none;
    padding: 0.95rem max(2rem, calc(50vw - 480px));
    font-family: 'Space Mono', monospace; font-size: 0.78rem; letter-spacing: 0.04em;
    margin-top: -2.6rem; margin-bottom: 2.6rem;
}
.topbar .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--ink); margin-right: 8px; vertical-align: -1px; }
.topbar .tag { color: var(--ink-soft); }

/* Hero with a premium italic serif headline */
.hero { text-align: center; margin-bottom: 1.2rem; }
.hero .eyebrow {
    font-family: 'Space Mono', monospace; text-transform: uppercase; letter-spacing: 0.28em;
    font-size: 0.74rem; color: var(--ink-soft); margin-bottom: 0.9rem;
}
.hero h1 {
    font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 600;
    font-size: clamp(2.7rem, 6vw, 4.2rem); line-height: 1.0; letter-spacing: -0.015em;
    margin: 0; color: var(--ink);
}
.hero p {
    color: var(--ink-soft); font-size: 1.02rem; line-height: 1.6; max-width: 600px; margin: 1rem auto 0 auto;
}

/* Composer */
.st-key-composer {
    border: 2px solid var(--line); border-radius: 18px; background: var(--card);
    box-shadow: var(--shadow-lg); padding: 0.5rem 0.9rem 0.6rem 0.9rem;
}
.st-key-composer textarea {
    border: none !important; box-shadow: none !important; background: transparent !important;
    font-size: 1.16rem !important; padding: 0.5rem 0.2rem !important; color: var(--ink) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.st-key-composer textarea::placeholder { color: rgba(26,26,23,0.4) !important; }
.st-key-composer [data-testid="stFileUploaderDropzone"] {
    background: transparent !important; border: 1.5px dashed rgba(26,26,23,0.3) !important;
    border-radius: 10px !important; padding: 0.4rem 0.8rem !important; min-height: unset !important;
}
.st-key-composer [data-testid="stFileUploaderDropzone"] section { padding: 0 !important; }

/* File chip for the preloaded PDF */
.file-chip {
    display: inline-flex; align-items: center; gap: 9px; border: 2px solid var(--line);
    border-radius: 10px; background: var(--paper); padding: 7px 12px; font-size: 0.86rem;
    box-shadow: 3px 3px 0 var(--line); max-width: 100%;
}
.file-chip .badge {
    font-family: 'Space Mono', monospace; font-size: 0.58rem; background: var(--ink); color: var(--paper);
    padding: 2px 5px; border-radius: 4px; letter-spacing: 0.06em;
}
.file-chip .muted { color: var(--ink-soft); font-family: 'Space Mono', monospace; font-size: 0.62rem; }
.st-key-rmpdf button {
    border-radius: 8px !important; padding: 0.1rem 0.5rem !important; min-height: 0 !important;
    box-shadow: 2px 2px 0 var(--line) !important; font-weight: 700 !important;
}

/* Minimal MCP popover */
.mcp-title { font-family: 'Space Mono', monospace; font-weight: 700; font-size: 0.78rem; letter-spacing: 0.12em; margin: 0 0 0.5rem 0; }
.st-key-mcp_add_more button {
    box-shadow: none !important; border-style: dashed !important; font-size: 0.76rem !important;
    opacity: 0.6; margin-top: 0.5rem;
}

label { color: var(--ink) !important; font-weight: 500 !important; }

/* Buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] > div button {
    background: var(--card); color: var(--ink); border: 2px solid var(--line); border-radius: 10px;
    box-shadow: var(--shadow); font-family: 'Space Grotesk', sans-serif; font-weight: 600;
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stPopover"] > div button:hover {
    transform: translate(-2px, -2px); box-shadow: var(--shadow-lg); background: #fff; color: var(--ink);
}
.stButton > button:active, .stDownloadButton > button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 #1a1a17; }
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--ink); color: var(--paper); border: 2px solid var(--ink); font-weight: 700; letter-spacing: 0.02em;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover { background: #000; color: #fff; }

/* The two hero popovers (but how / sample questions) sit quietly */
.st-key-hero-actions [data-testid="stPopover"] > div button {
    background: transparent; box-shadow: none; border: 2px solid rgba(26,26,23,0.25); opacity: 0.7;
    font-family: 'Space Mono', monospace; font-size: 0.78rem; text-transform: lowercase;
}
.st-key-hero-actions [data-testid="stPopover"] > div button:hover { opacity: 1; background: var(--card); box-shadow: var(--shadow); }

/* Expanders (reasoning), borderless */
[data-testid="stExpander"] { border: none !important; background: transparent !important; box-shadow: none !important; }
[data-testid="stExpander"] details { border: none !important; background: transparent !important; }
[data-testid="stExpander"] summary {
    font-family: 'Space Mono', monospace !important; text-transform: uppercase; letter-spacing: 0.06em;
    font-size: 0.76rem; color: var(--ink-soft) !important; padding-left: 0 !important;
}

/* Result page */
.result-q {
    font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 600;
    font-size: clamp(1.7rem, 3.5vw, 2.4rem); line-height: 1.12; color: var(--ink); margin: 0.4rem 0 0.2rem 0;
}
.back-link { font-family: 'Space Mono', monospace; font-size: 0.74rem; color: var(--ink-soft); letter-spacing: 0.06em; }

.rule { display: flex; align-items: center; gap: 1rem; margin: 2.2rem 0 1.1rem 0; }
.rule:before, .rule:after { content: ""; flex: 1; height: 2px; background: var(--line); opacity: 0.4; }
.rule span { font-family: 'Space Mono', monospace; text-transform: uppercase; letter-spacing: 0.2em; font-size: 0.74rem; color: var(--ink-soft); }

.st-key-answer-card {
    border: 2px solid var(--line); border-radius: 12px; background: var(--card);
    box-shadow: var(--shadow-lg); padding: 1.4rem 1.7rem;
}
.mono-tag { font-family: 'Space Mono', monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.16em; color: var(--ink-soft); margin-bottom: 0.4rem; }
.st-key-answer-card p, .st-key-answer-card li { color: var(--ink); line-height: 1.7; }

.chip-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.2rem 0 1rem 0; }
.chip { font-family: 'Space Mono', monospace; border: 2px solid var(--line); border-radius: 999px; padding: 0.25rem 0.75rem; font-size: 0.74rem; background: var(--paper); color: var(--ink); }
.chip.on { background: var(--ink); color: var(--paper); }

.footer-note { font-family: 'Space Mono', monospace; color: var(--ink-soft); font-size: 0.74rem; text-align: center; margin-top: 3rem; letter-spacing: 0.04em; }
.diagram-cap { font-family: 'Space Mono', monospace; font-size: 0.74rem; color: var(--ink-soft); margin-top: 0.4rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_agent():
    from agent import build_agent
    return build_agent()


def run_agent(question: str, business_context: str) -> dict:
    agent = get_agent()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_state = {"question": question, "business_context": business_context or "", "attempts": 0}
    return agent.invoke(initial_state, config=config)


# ---------------------------------------------------------------------------
# Context: preloaded PDF + any uploaded files
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_preloaded_context() -> str:
    try:
        import fitz
        with fitz.open(PRELOADED_PDF_PATH) as doc:
            return "\n".join(p.get_text() for p in doc).strip()
    except Exception:
        return ""


def extract_file_text(uploaded_files) -> str:
    chunks = []
    for f in uploaded_files or []:
        name = (f.name or "").lower()
        data = f.getvalue()
        try:
            if name.endswith(".pdf"):
                import fitz
                with fitz.open(stream=data, filetype="pdf") as doc:
                    text = "\n".join(page.get_text() for page in doc)
            elif name.endswith(".docx"):
                from docx import Document
                document = Document(io.BytesIO(data))
                text = "\n".join(p.text for p in document.paragraphs)
            else:
                text = data.decode("utf-8", errors="ignore")
        except Exception as exc:
            text = f"(Could not read this file: {exc})"
        text = (text or "").strip()
        if text:
            chunks.append(f"--- From file: {f.name} ---\n{text}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# PDF report: diagram on top, then question and answer. Compact. No context.
# ---------------------------------------------------------------------------
from fpdf import FPDF

BODY_FONT = "Helvetica"
DARK = (26, 26, 23)
INK = (33, 33, 30)
MUTED = (110, 108, 100)

_REPLACE = {
    chr(0x2014): "-", chr(0x2013): "-", chr(0x2018): "'", chr(0x2019): "'",
    chr(0x201c): '"', chr(0x201d): '"', chr(0x2022): "-", chr(0x2026): "...",
    chr(0x00a0): " ", chr(0x2192): "->", chr(0x2009): " ", chr(0x200b): "",
    chr(0x00ad): "", chr(0x2011): "-",
}


def _ascii(text) -> str:
    text = str(text if text is not None else "")
    for bad, good in _REPLACE.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def _md_for_pdf(text: str) -> str:
    import re
    out = []
    for line in str(text or "").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            line = "**" + stripped.lstrip("#").strip() + "**"
        else:
            line = line.rstrip()
            line = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", r"**\1**", line)
        out.append(line)
    return "\n".join(out)


class ReportPDF(FPDF):
    report_date = ""

    def header(self):
        self.set_fill_color(*DARK)
        self.rect(0, 0, self.w, 16, "F")
        self.set_xy(self.l_margin, 4)
        self.set_font(BODY_FONT, "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "NIMBUS ANALYTICS", align="L")
        self.set_xy(self.l_margin, 4)
        self.set_font(BODY_FONT, "", 9)
        self.set_text_color(200, 198, 188)
        self.cell(self.w - self.l_margin - self.r_margin, 8,
                  _ascii(f"Company Intelligence Report   |   {self.report_date}"), align="R")
        self.set_y(23)

    def footer(self):
        self.set_y(-13)
        self.set_draw_color(200, 198, 188)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_font(BODY_FONT, "", 8)
        self.set_text_color(*MUTED)
        self.set_xy(self.l_margin, self.get_y())
        self.cell(0, 9, _ascii(f"Nimbus Analytics  |  Confidential  |  Generated {self.report_date}"), align="L")
        self.set_xy(self.l_margin, self.get_y())
        self.cell(self.w - self.l_margin - self.r_margin, 9, f"Page {self.page_no()}", align="R")

    def section_label(self, text):
        self.set_font(BODY_FONT, "B", 10)
        self.set_text_color(60, 58, 52)
        self.cell(0, 5.5, _ascii(text))
        self.ln(6)


def build_report_pdf(question, answer, diagram_png=None) -> bytes:
    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.report_date = datetime.date.today().strftime("%B %d, %Y")
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(15, 20, 15)
    pdf.add_page()
    avail = pdf.w - pdf.l_margin - pdf.r_margin

    # Compact title
    pdf.set_font(BODY_FONT, "B", 19)
    pdf.set_text_color(26, 26, 23)
    pdf.cell(0, 9, "Company Intelligence Report")
    pdf.ln(9)
    pdf.set_fill_color(26, 26, 23)
    pdf.rect(pdf.l_margin, pdf.get_y(), avail, 0.9, "F")
    pdf.ln(4.5)

    # Question
    pdf.section_label("QUESTION")
    pdf.set_font(BODY_FONT, "", 11)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.6, _ascii(question))
    pdf.ln(3)

    # Flow diagram on top (before the answer)
    if diagram_png:
        from PIL import Image
        px_w, px_h = Image.open(io.BytesIO(diagram_png)).size
        ratio = px_h / px_w
        img_w = avail
        img_h = img_w * ratio
        max_h = 165
        if img_h > max_h:
            img_h = max_h
            img_w = img_h / ratio
        if pdf.get_y() + img_h > pdf.h - 16:
            pdf.add_page()
        pdf.section_label("FLOW DIAGRAM")
        x = pdf.l_margin + (avail - img_w) / 2
        pdf.image(io.BytesIO(diagram_png), x=x, w=img_w)
        pdf.ln(4)

    # Answer
    pdf.section_label("ANSWER")
    pdf.set_font(BODY_FONT, "", 10.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.8, _ascii(_md_for_pdf(answer)), markdown=True)

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Copy to clipboard (runs inside a small component iframe)
# ---------------------------------------------------------------------------
def copy_button(text, label="Copy answer"):
    payload = json.dumps(text)
    html = """
    <style>
      .cpy { font-family: 'Space Mono', monospace; font-size: 12px; cursor: pointer;
        background: #fbf9f3; color: #1a1a17; border: 2px solid #1a1a17; border-radius: 10px;
        padding: 6px 14px; box-shadow: 3px 3px 0 #1a1a17; }
      .cpy:active { transform: translate(2px,2px); box-shadow: 1px 1px 0 #1a1a17; }
    </style>
    <button class="cpy" id="cpy" onclick="copyIt()">__LABEL__</button>
    <script>
      const txt = __PAYLOAD__;
      function copyIt() {
        const ta = document.createElement('textarea'); ta.value = txt;
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(ta);
        const b = document.getElementById('cpy'); const old = b.innerText;
        b.innerText = 'Copied'; setTimeout(() => { b.innerText = old; }, 1200);
      }
    </script>
    """
    html = html.replace("__LABEL__", label).replace("__PAYLOAD__", payload)
    components.html(html, height=46)


@st.dialog("Flow diagram", width="large")
def show_diagram_dialog(png):
    """Maximized view of the flow diagram. The dialog's close button minimizes it."""
    st.image(png, width="stretch")
    st.download_button(
        "Download diagram (PNG)", data=png, file_name="flow_diagram.png",
        mime="image/png", width="content",
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
DEFAULTS = {
    "question": "",
    "ctx_pdf_kept": True,
    "pending_run": False,
    "result": None,
    "result_question": "",
    "result_context": "",
    "result_excalidraw": True,
    "diagram": None,
    "report_pdf": None,
    "run_error": "",
}
for key, default in DEFAULTS.items():
    st.session_state.setdefault(key, default)
for c in CONNECTORS:
    st.session_state.setdefault(f"conn_{c['key']}", c["default"])


def fill_question(text: str):
    st.session_state["question"] = text


def remove_pdf():
    st.session_state["ctx_pdf_kept"] = False


BUT_HOW = (
    "You ask a question. The agent works out what company information it needs, then "
    "securely reaches into your own data: the metrics, the support tickets, and the "
    "internal documents. It reads what it finds and checks whether the evidence is strong "
    "enough to answer. If it is not, it looks again. Only then does it write the answer, and "
    "every point is tied back to your real data. So you get a decision you can trust, not a guess."
)


def topbar():
    st.markdown(
        """
        <div class="topbar">
          <div><span class="dot"></span>NIMBUS ANALYTICS</div>
          <div class="tag">COMPANY INTELLIGENCE AGENT</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE 1: ASK
# ===========================================================================
def render_home():
    topbar()

    # Once an answer exists, offer a way back into it (kept in session, no re-run)
    if st.session_state.get("result"):
        _, nav = st.columns([7, 3])
        with nav:
            if st.button("View last insights", key="view_last", width="stretch"):
                st.switch_page(results_page)

    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">Secure / grounded / no hallucination</div>
          <h1>Ask anything about your business.</h1>
          <p>An AI agent that securely connects to your company data and turns it into
             strategic decisions, grounded in real evidence with no hallucination.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Two quiet actions, side by side
    with st.container(key="hero-actions"):
        _, a1, a2, _ = st.columns([2, 3, 3, 2])
        with a1:
            with st.popover("but how?", width="stretch"):
                st.markdown("**How the agent works**")
                st.write(BUT_HOW)
        with a2:
            with st.popover("need a starting point?", width="stretch"):
                st.markdown("**Sample questions**")
                for demo_q in DEMO_QUESTIONS:
                    st.button(demo_q, key=f"demo_{demo_q}", on_click=fill_question,
                              args=(demo_q,), width="stretch")

    st.write("")

    # ---- The composer ----
    with st.container(key="composer"):
        st.text_area(
            "Your question",
            key="question",
            label_visibility="collapsed",
            height=92,
            placeholder="Ask a business question, or attach docs and ask about them...",
        )

        # Preloaded business context shows as a removable chip. The upload
        # button only appears once that preloaded document has been removed.
        uploaded = None
        if st.session_state["ctx_pdf_kept"]:
            chip_l, chip_r = st.columns([12, 1])
            with chip_l:
                st.markdown(
                    f'<div class="file-chip"><span class="badge">PDF</span>{PRELOADED_PDF_NAME}'
                    f'<span class="muted">preloaded</span></div>',
                    unsafe_allow_html=True,
                )
            with chip_r:
                with st.container(key="rmpdf"):
                    st.button("x", key="remove_pdf", on_click=remove_pdf, help="Remove this document")
        else:
            uploaded = st.file_uploader(
                "Attach documents",
                type=["pdf", "docx", "txt", "md"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                key="composer_files",
            )

        tool_l, tool_r = st.columns([1, 6])
        with tool_l:
            with st.container(key="mcp-pop"):
                with st.popover("+", help="MCP", width="content"):
                    st.markdown('<div class="mcp-title">MCP</div>', unsafe_allow_html=True)
                    for c in CONNECTORS:
                        st.toggle(c["name"], key=f"conn_{c['key']}")
                    st.button("add more", key="mcp_add_more", disabled=True, width="stretch")
        with tool_r:
            ask = st.button("Ask the Agent", type="primary", width="stretch")

    st.markdown(
        '<div class="footer-note">Personalized AI agent for your company</div>',
        unsafe_allow_html=True,
    )

    # ---- Submit ----
    if ask:
        question = (st.session_state["question"] or "").strip()
        if not question:
            st.warning("Please type a question first, or open the sample questions above.")
        else:
            parts = []
            if st.session_state["ctx_pdf_kept"]:
                pre = load_preloaded_context()
                if pre:
                    parts.append(f"--- From file: {PRELOADED_PDF_NAME} ---\n{pre}")
            file_text = extract_file_text(uploaded)
            if file_text:
                parts.append(file_text)

            st.session_state["result_question"] = question
            st.session_state["result_context"] = ("\n\n".join(parts))[:9000]
            st.session_state["result_excalidraw"] = bool(st.session_state.get("conn_excalidraw"))
            st.session_state["pending_run"] = True
            st.session_state["result"] = None
            st.session_state["diagram"] = None
            st.session_state["report_pdf"] = None
            st.session_state["run_error"] = ""
            st.switch_page(results_page)


# ===========================================================================
# PAGE 2: INSIGHTS
# ===========================================================================
def render_results():
    topbar()

    if st.session_state["pending_run"]:
        question = st.session_state["result_question"]
        context = st.session_state["result_context"]
        with st.spinner("The agent is planning, securely retrieving company data, and checking "
                        "its evidence. This can take up to a minute on the first run..."):
            try:
                st.session_state["result"] = run_agent(question, context)
            except Exception as exc:
                st.session_state["run_error"] = str(exc)

        result = st.session_state["result"]
        if result and st.session_state["result_excalidraw"]:
            with st.spinner("Building the flow diagram..."):
                try:
                    st.session_state["diagram"] = generate_diagram(
                        question, result.get("final_answer", "") or "")
                except Exception:
                    st.session_state["diagram"] = None

        if result:
            try:
                diagram = st.session_state.get("diagram")
                dpng = diagram.image_png if diagram else None
                st.session_state["report_pdf"] = build_report_pdf(
                    question, result.get("final_answer", "") or "", dpng)
            except Exception:
                st.session_state["report_pdf"] = None

        st.session_state["pending_run"] = False

    st.markdown('<div class="back-link">', unsafe_allow_html=True)
    if st.button("Back to ask the agent", width="content"):
        st.switch_page(home_page)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state["run_error"]:
        st.error(f"The agent could not complete the run: {st.session_state['run_error']}")
        return

    result = st.session_state["result"]
    if not result:
        st.info("No question has been asked yet. Head back to ask the agent.")
        return

    question = st.session_state["result_question"]
    final_answer = result.get("final_answer", "") or "The agent did not return an answer."

    st.write("")
    st.markdown(f'<div class="result-q">{question}</div>', unsafe_allow_html=True)

    diagram = st.session_state.get("diagram")
    show_diagram = bool(st.session_state["result_excalidraw"] and diagram and diagram.image_png)

    def render_answer():
        with st.container(key="answer-card"):
            st.markdown('<div class="mono-tag">Grounded answer</div>', unsafe_allow_html=True)
            st.markdown(final_answer)
        copy_button(final_answer, "Copy answer")

    def render_diagram():
        st.image(diagram.image_png, width="stretch")
        if st.button("Maximize", key="max_diagram", width="content"):
            show_diagram_dialog(diagram.image_png)
        if diagram.link:
            st.markdown(
                f'<div class="diagram-cap">'
                f'<a href="{diagram.link}" target="_blank" rel="noopener noreferrer">'
                f'Open in Excalidraw &rarr;</a></div>',
                unsafe_allow_html=True,
            )
        elif diagram.source == "local":
            st.markdown('<div class="diagram-cap">Local preview. Connect the Excalidraw MCP '
                        '(see EXCALIDRAW_MCP_SETUP.md) to render it on a real Excalidraw board.</div>',
                        unsafe_allow_html=True)

    # ----- Answer and flow diagram, side by side -----
    if show_diagram:
        st.markdown('<div class="rule"><span>Answer &amp; flow diagram</span></div>', unsafe_allow_html=True)
        col_ans, col_diag = st.columns(2, gap="large")
        with col_ans:
            render_answer()
        with col_diag:
            render_diagram()
    else:
        st.markdown('<div class="rule"><span>Answer</span></div>', unsafe_allow_html=True)
        render_answer()
        if st.session_state["result_excalidraw"]:
            st.caption("The diagram could not be generated for this answer.")

    # ----- Reasoning -----
    attempts = int(result.get("attempts", 0) or 0)
    loop_fired = attempts > 1
    sufficient = bool(result.get("evidence_sufficient", False))
    st.write("")
    with st.expander("How the agent reasoned", expanded=False):
        suff_chip = ('<span class="chip on">Evidence sufficient</span>' if sufficient
                     else '<span class="chip">Evidence judged thin</span>')
        loop_chip = ('<span class="chip on">Self-correcting loop fired</span>' if loop_fired
                     else '<span class="chip">Answered on first pass</span>')
        st.markdown(
            f'<div class="chip-row"><span class="chip">Retrieval attempts: {attempts}</span>'
            f'{loop_chip}{suff_chip}</div>', unsafe_allow_html=True)
        st.markdown("**Plan**")
        st.markdown(result.get("plan", "") or "No plan was recorded.")
        st.markdown("**Evaluator's verdict**")
        st.markdown(result.get("evidence_reason", "") or "No evaluator reason was recorded.")
        with st.expander("Show the raw retrieved evidence", expanded=False):
            st.markdown("**Structured metrics (Genie)**")
            st.code(result.get("genie_result", "") or "(empty)", language="text")
            st.markdown("**Support tickets**")
            st.code(result.get("ticket_result", "") or "(empty)", language="text")
            st.markdown("**Internal documents**")
            st.code(result.get("doc_result", "") or "(empty)", language="text")

    # ----- Report -----
    st.markdown('<div class="rule"><span>Report</span></div>', unsafe_allow_html=True)
    if st.session_state["report_pdf"]:
        today = datetime.date.today().isoformat()
        st.download_button(
            "Download report (PDF)",
            data=st.session_state["report_pdf"],
            file_name=f"Nimbus_Analytics_Report_{today}.pdf",
            mime="application/pdf",
            width="content",
        )
    else:
        st.caption("The report could not be generated.")

    st.markdown(
        '<div class="footer-note">Personalized AI agent for your company</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Pages and navigation
# ---------------------------------------------------------------------------
home_page = st.Page(render_home, title="Ask", url_path="ask", default=True)
results_page = st.Page(render_results, title="Insights", url_path="insights")

if __name__ == "__main__":
    st.navigation([home_page, results_page], position="hidden").run()
