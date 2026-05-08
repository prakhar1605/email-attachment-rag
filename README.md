# Email + Attachment RAG with Thread Memory

A focused RAG chatbot that answers questions about email threads and their attachments, with conversation memory and grounded citations.

## Features

- ✅ Parse `.eml` files + extract text from PDFs (page-level), DOCX, TXT, HTML
- ✅ BM25 retrieval scoped to a chosen thread
- ✅ Conversation memory (last 5 turns) + entity tracking (people, dates, amounts, filenames)
- ✅ Query rewriting using LLM (resolves pronouns like "that", "it")
- ✅ Grounded answers with inline citations: `[msg: m_9b2]` / `[msg: m_9b2, page: 2]`
- ✅ FastAPI backend + Streamlit UI with debug panel
- ✅ Per-turn JSONL trace logs
- ✅ Docker-compose ready

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a free Groq API key
Sign up at https://console.groq.com → create API key → set environment variable:
```bash
export GROQ_API_KEY="your_key_here"
```

### 3. Create sample dataset
```bash
python create_sample_data.py
```
This creates 8 emails across 3 threads with 4 PDF attachments in `data/raw/`.

### 4. Build the index
```bash
python ingest.py
```
This produces `data/processed/chunks.json`, `bm25.pkl`, and `threads.json`.

### 5. Run

**Option A — Local (two terminals):**
```bash
# Terminal 1: API
uvicorn api:app --reload --port 8000

# Terminal 2: UI
streamlit run app.py
```
Open http://localhost:8501

**Option B — Docker:**
```bash
export GROQ_API_KEY="your_key_here"
docker compose up --build
```
Open http://localhost:8501 (UI) and http://localhost:8000/docs (API)

## API Endpoints

| Method | Path | Body |
|---|---|---|
| POST | `/start_session` | `{"thread_id": "T-0001"}` |
| POST | `/ask` | `{"session_id": "...", "text": "...", "search_outside_thread": false}` |
| POST | `/switch_thread` | `{"session_id": "...", "thread_id": "..."}` |
| POST | `/reset_session` | `{"session_id": "..."}` |
| GET | `/threads` | - |

## Architecture