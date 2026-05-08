# Email + Attachment RAG with Thread Memory

A focused RAG chatbot that answers questions about email threads and their attachments, with conversation memory and grounded citations.

## 🎥 Demo Video

Watch the 4-minute demo here: https://youtu.be/rCBt8uSDXGE

The demo covers:

* Thread selection
* Factual question answering with citations
* Pronoun resolution
* Multi-document comparison
* Graceful failure handling
* Trace logs

---

# Features

✅ Parse `.eml` files + extract text from PDFs (page-level), DOCX, TXT, HTML
✅ BM25 retrieval scoped to a chosen thread
✅ Conversation memory (last 5 turns) + entity tracking (people, dates, amounts, filenames)
✅ Query rewriting using LLM (resolves pronouns like "that", "it")
✅ Grounded answers with inline citations: `[msg: m_9b2]` / `[msg: m_9b2, page: 2]`
✅ FastAPI backend + Streamlit UI with debug panel
✅ Per-turn JSONL trace logs
✅ Docker-compose ready

---

# Setup

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Get a free Groq API key

Sign up at: https://console.groq.com

Create a `.env` file:

```bash
echo 'GROQ_API_KEY=your_key_here' > .env
```

## 3. Create sample dataset

```bash
python create_sample_data.py
```

This creates:

* 8 emails across 3 threads
* 4 PDF attachments

Stored in:

```bash
data/raw/
```

## 4. Build the index

```bash
python ingest.py
```

Produces:

* `data/processed/chunks.json`
* `bm25.pkl`
* `threads.json`

## 5. Run the project

### Option A — Local (two terminals)

#### Terminal 1 — API

```bash
uvicorn api:app --reload --port 8000
```

#### Terminal 2 — Streamlit UI

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

### Option B — Docker

```bash
export GROQ_API_KEY="your_key_here"
docker compose up --build
```

---

# API Endpoints

| Method | Path             | Body                                                                   |
| ------ | ---------------- | ---------------------------------------------------------------------- |
| POST   | `/start_session` | `{"thread_id": "T-0001"}`                                              |
| POST   | `/ask`           | `{"session_id": "...", "text": "...", "search_outside_thread": false}` |
| POST   | `/switch_thread` | `{"session_id": "...", "thread_id": "..."} `                           |
| POST   | `/reset_session` | `{"session_id": "..."} `                                               |
| GET    | `/threads`       | List all available threads                                             |

---

# Architecture

```text
[.eml files + PDFs]
       ↓
   ingest.py
       ↓
chunks.json + bm25.pkl + threads.json
       ↓
[Streamlit UI] ⟷ [FastAPI]
                      ↓
     [Retriever → Rewriter → Answerer]
                      ↓
         Groq llama-3.1-8b-instant
                      ↓
               trace.jsonl
```

---

# Pipeline Per Query

### 1. Rewrite

Query is rewritten into a standalone query using:

* Last 5 turns
* Tracked entities
* Groq LLM

### 2. Retrieve

BM25 search over indexed chunks filtered to the active thread.

### 3. Answer

Strict grounded-answer prompt with evidence + citation rules.

### 4. Log

Full execution trace appended to:

```bash
runs/<timestamp>/trace.jsonl
```

---

# Design Choices

### BM25 over Vector Search

Assignment baseline. Emails contain highly specific lexical terms (names, dates, amounts, filenames) where BM25 performs strongly.

Can later be extended with vector search using hybrid/late fusion retrieval.

### Subject-based Threading Fallback

Primary:

* `In-Reply-To` header

Fallback:

* Subject normalization (`Re:`, `Fwd:` stripping)

### One Chunk per Email Body

Emails are short and self-contained, so chunk splitting is unnecessary.

### Page-aware PDF Chunking

Each PDF page:

* Extracted separately
* Chunked into ~300-token chunks
* 50-token overlap

This preserves accurate page citations.

### LLM-based Query Rewriting

Groq LLM handles pronoun resolution more reliably than regex/rule-based systems.

### Strict Citation Prompting

Model must:

* Cite every factual claim
* Refuse unsupported answers gracefully

### Streamlit + FastAPI Separation

Clean frontend/backend separation enables future frontend replacement easily.

---

# Known Limitations

* BM25 misses semantic matches (e.g. "approval" vs "sign-off")
* Subject-based threading can fail if subjects are reused
* No OCR support for scanned PDFs
* Sessions stored in-memory only (restart clears sessions)

---

# Performance

* Average latency: ~1.5–2.5s per query
* BM25 retrieval: sub-50ms
* Majority latency from Groq LLM call (~800ms–1.5s)

Latency metrics are logged in:

```bash
latency_ms
```

inside each trace record.

---

# Testing

See:

```bash
sample_questions.md
```

Covers:

* Factual lookup
* Pronoun resolution
* Ellipsis
* Corrections
* Comparisons
* Timelines
* Graceful failure

---

# File Structure

| File                    | Purpose                              |
| ----------------------- | ------------------------------------ |
| `create_sample_data.py` | Generates synthetic email dataset    |
| `ingest.py`             | Parses emails + builds BM25 index    |
| `core/retriever.py`     | BM25 retrieval with thread filtering |
| `core/memory.py`        | Session memory + entity tracking     |
| `core/rewriter.py`      | Query rewriting using Groq           |
| `core/answerer.py`      | Grounded answer generation           |
| `api.py`                | FastAPI backend                      |
| `app.py`                | Streamlit frontend                   |
| `runs/<ts>/trace.jsonl` | Per-turn trace logs                  |

---

# Tech Stack

### Backend

* FastAPI
* Uvicorn

### UI

* Streamlit

### Retrieval

* rank-bm25

### LLM

* Groq API (`llama-3.1-8b-instant`)

### Document Parsing

* PyMuPDF (PDF)
* python-docx (DOCX)
* BeautifulSoup4 (HTML)

### Containerization

* Docker
* docker-compose
