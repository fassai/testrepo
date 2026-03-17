# NotebookLM-Claude

A NotebookLM-style research assistant powered by Claude. Upload your documents and have grounded, source-cited conversations about them.

## Features

- **Upload multiple sources** – text files, Jupyter notebooks (.ipynb), Python scripts, CSVs, Markdown, JSON
- **Grounded answers** – Claude answers only from your uploaded sources and cites them by name
- **Quick actions** – one-click "Summarise all" and "Key ideas" buttons
- **Model selection** – choose between Claude Sonnet, Haiku, or Opus
- **Chat history** – full multi-turn conversation context

## Setup

```bash
cd notebooklm_claude
pip install -r requirements.txt
```

## Run

```bash
# Option A: set your API key as an env var
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py

# Option B: paste your API key in the sidebar when the app opens
streamlit run app.py
```

## Usage

1. Open the app in your browser (Streamlit will show the URL)
2. Enter your Anthropic API key in the sidebar (or set it as an env var)
3. Upload one or more documents via the sidebar file uploader
4. Ask questions in the chat — Claude will answer using only your sources
5. Use the **Summarise all** or **Key ideas** buttons for quick overviews
