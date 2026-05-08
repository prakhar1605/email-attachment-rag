# Email + Attachment RAG with Thread Memory

A focused RAG chatbot that answers questions about email threads and their attachments, with conversation memory and grounded citations.

## 🎥 Demo Video

**[Watch the 4-minute demo here](https://youtu.be/sWtzaTdfGyU)**

The demo covers: thread selection → factual question with citations → pronoun resolution → multi-document comparison → graceful failure → trace logs.

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
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Get a free Groq API key
Sign up at https://console.groq.com → create API key → create a `.env` file:
\`\`\`bash
echo 'GROQ_API_KEY=your_key_here' > .env
\`\`\`

### 3. Create sample dataset
\`\`\`bash
python create_sample_data.py
\`\`\`
This creates 8 emails across 3 threads with 4 PDF attachments in `data/raw/`.

### 4. Build the index
\`\`\`bash
python ingest.py
\`\`\`
Produces `data/processed/chunks.json`, `bm25.pkl`, and `threads.json`.

### 5. Run

**Option A — Local (two terminals):**
\`\`\`bash
# Terminal 1: API
uvicorn api:app --reload --port 8000

# Terminal 2: UI
streamlit run app.py
\`\`\`
Open http://localhost:8501

**Option B — Docker:**
\`\`\`bash
export GROQ_API_KEY="your_key_here"
docker compose up --build
\`\`\`

## API Endpoints

| Method | Path | Body |
|---|---|---|
| POST | `/start_session` | `{"thread_id": "T-0001"}` |
| POST | `/ask` | `{"session_id": "...", "text": "...", "search_outside_thread": false}` |
| POST | `/switch_thread` | `{"session_id": "...", "thread_id": "..."}` |
| POST | `/reset_session` | `{"session_id": "..."}` |
| GET | `/threads` | List all available threads |

## Architecture

\`\`\`
[.eml files + PDFs]
       ↓
   ingest.py  →  chunks.json + bm25.pkl + threads.json
       ↓
[Streamlit UI] ⟷ [FastAPI] → [Retriever → Rewriter → Answerer (Groq llama-3.1-8b)]
                                        ↓
                                  trace.jsonl
\`\`\`

**Pipeline per query:**
1. **Rewrite** — Query is rewritten to be standalone using last 5 turns + tracked entities (Groq LLM)
2. **Retrieve** — BM25 search over chunks, filtered to active thread
3. **Answer** — Strict-prompt LLM call with evidence + citation rules
4. **Log** — Full trace appended to `runs/<timestamp>/trace.jsonl`

## Design Choices

- **BM25 over vectors**: Assignment baseline. Emails contain specific terms (names, amounts, dates) where lexical search excels. Easily extensible to vector search via late fusion.
- **Subject-based threading fallback**: `In-Reply-To` header is primary; subject normalization (stripping `Re:`/`Fwd:`) is the fallback.
- **One chunk per email body**: Emails are short and self-contained — no need to split.
- **Page-aware PDF chunking**: Each PDF page → text → 300-token chunks (50 overlap). This preserves the page number for citations.
- **LLM rewriter over rule-based**: Pronoun resolution via Groq is more reliable than regex rules.
- **Strict citation prompt**: Forces the model to cite every claim or refuse to answer (graceful failure).
- **Streamlit + FastAPI separation**: API exposes the 4 required endpoints; Streamlit calls them. Clean boundary for future frontend swap.

## Known Limitations

- BM25 misses semantic matches (e.g., "approval" vs "sign-off"). Vector search would help — easy to add.
- Subject-based threading fails if subjects are reused; `In-Reply-To` covers most real cases.
- No OCR for scanned PDFs (only text-based PDFs).
- In-memory sessions — server restart loses session state.

## Performance

- Lexical-only path: ~1.5-2.5s per turn (warm cache, top-k=8)
- Latency dominated by Groq LLM call (~800ms-1.5s); BM25 is sub-50ms
- Logged in every trace record under `latency_ms`

## Testing

See `sample_questions.md` for 7 sample questions covering: factual lookup, pronoun resolution, ellipsis, correction, comparison, timeline, and graceful failure.

## File Structure

| File | Purpose |
|---|---|
| `create_sample_data.py` | Generates synthetic dataset (.eml + PDFs) |
| `ingest.py` | Parses emails, builds BM25 index |
| `core/retriever.py` | BM25 search with thread filter |
| `core/memory.py` | Session memory + entity extraction |
| `core/rewriter.py` | Query rewriting via Groq |
| `core/answerer.py` | Grounded answer generation with citation parsing |
| `api.py` | FastAPI endpoints |
| `app.py` | Streamlit UI |
| `runs/<ts>/trace.jsonl` | Per-turn execution logs |
