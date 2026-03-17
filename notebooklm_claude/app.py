"""
NotebookLM-Claude: A NotebookLM-style app powered by Claude.

Upload documents (PDFs, text files, Jupyter notebooks) and have
AI-powered conversations grounded in your content.
"""

import os
import json
import hashlib
import streamlit as st
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Helpers – document parsing
# ---------------------------------------------------------------------------

def parse_text_file(uploaded_file) -> str:
    return uploaded_file.getvalue().decode("utf-8", errors="replace")


def parse_jupyter_notebook(uploaded_file) -> str:
    """Extract markdown and code cells from a .ipynb file."""
    nb = json.loads(uploaded_file.getvalue().decode("utf-8"))
    parts: list[str] = []
    for i, cell in enumerate(nb.get("cells", []), 1):
        ctype = cell.get("cell_type", "code")
        source = "".join(cell.get("source", []))
        parts.append(f"--- Cell {i} ({ctype}) ---\n{source}")
    return "\n\n".join(parts)


def parse_uploaded_file(uploaded_file) -> str:
    """Return the text content of an uploaded file."""
    name = uploaded_file.name.lower()
    if name.endswith(".ipynb"):
        return parse_jupyter_notebook(uploaded_file)
    # Treat everything else as plain text (txt, py, md, csv, …)
    return parse_text_file(uploaded_file)


def file_id(uploaded_file) -> str:
    return hashlib.md5(uploaded_file.getvalue()).hexdigest()

# ---------------------------------------------------------------------------
# Claude interaction
# ---------------------------------------------------------------------------

def build_system_prompt(sources: dict[str, str]) -> str:
    """Build a system prompt that grounds Claude in the uploaded sources."""
    if not sources:
        return (
            "You are a helpful research assistant. "
            "No documents have been uploaded yet — let the user know they "
            "can upload files in the sidebar."
        )

    docs_text = "\n\n".join(
        f"=== SOURCE: {name} ===\n{content}" for name, content in sources.items()
    )
    return (
        "You are NotebookLM-Claude, an expert research assistant. "
        "The user has uploaded the following source documents. "
        "Answer questions accurately using ONLY information from these sources. "
        "When you reference a source, cite it by name. "
        "If the answer is not in the sources, say so clearly.\n\n"
        f"{docs_text}"
    )


def get_client() -> Anthropic:
    api_key = st.session_state.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Please provide your Anthropic API key in the sidebar.")
        st.stop()
    return Anthropic(api_key=api_key)

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="NotebookLM-Claude", page_icon="📓", layout="wide")
st.title("📓 NotebookLM-Claude")
st.caption("Upload your documents and chat with Claude about them — powered by Claude API")

# ---- Sidebar: config & uploads ----
with st.sidebar:
    st.header("Settings")
    st.text_input(
        "Anthropic API Key",
        type="password",
        key="api_key",
        help="Or set the ANTHROPIC_API_KEY env var.",
    )
    model = st.selectbox(
        "Model",
        ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001", "claude-opus-4-20250514"],
        index=0,
    )

    st.divider()
    st.header("Sources")
    uploaded_files = st.file_uploader(
        "Upload documents",
        accept_multiple_files=True,
        type=["txt", "md", "py", "ipynb", "csv", "json", "log"],
        help="Upload text files, notebooks, code, CSVs, etc.",
    )

# ---- Parse & index uploaded files ----
if "sources" not in st.session_state:
    st.session_state.sources: dict[str, str] = {}

if uploaded_files:
    for uf in uploaded_files:
        fid = file_id(uf)
        if fid not in st.session_state.sources:
            st.session_state.sources[fid] = {
                "name": uf.name,
                "content": parse_uploaded_file(uf),
            }

# Show loaded sources in the sidebar
with st.sidebar:
    if st.session_state.sources:
        st.success(f"{len(st.session_state.sources)} source(s) loaded")
        for src in st.session_state.sources.values():
            st.markdown(f"- **{src['name']}**")
        if st.button("Clear all sources"):
            st.session_state.sources = {}
            st.session_state.messages = []
            st.rerun()
    else:
        st.info("Upload documents to get started.")

    st.divider()
    st.header("Quick actions")
    col1, col2 = st.columns(2)
    summarise = col1.button("Summarise all")
    key_ideas = col2.button("Key ideas")

# ---- Chat state ----
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []

# Handle quick-action buttons
if summarise:
    st.session_state.messages.append(
        {"role": "user", "content": "Summarise each uploaded source document concisely."}
    )
if key_ideas:
    st.session_state.messages.append(
        {"role": "user", "content": "List the key ideas and themes across all uploaded sources."}
    )

# ---- Render chat history ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- Chat input ----
if prompt := st.chat_input("Ask about your documents…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# ---- Generate assistant response when last message is from user ----
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    sources_map = {v["name"]: v["content"] for v in st.session_state.sources.values()}
    system_prompt = build_system_prompt(sources_map)

    client = get_client()

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            )
            assistant_text = response.content[0].text

        st.markdown(assistant_text)
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_text}
        )
