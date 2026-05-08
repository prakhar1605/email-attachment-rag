Email + Attachment RAG with Thread MemoryA focused RAG chatbot that answers questions about email threads and their attachments, with conversation memory and grounded citations.🎥 Demo VideoWatch the 4-minute demo hereThe demo covers: thread selection → factual question with citations → pronoun resolution → multi-document comparison → graceful failure → trace logs.Features
✅ Parse .eml files + extract text from PDFs (page-level), DOCX, TXT, HTML
✅ BM25 retrieval scoped to a chosen thread
✅ Conversation memory (last 5 turns) + entity tracking (people, dates, amounts, filenames)
✅ Query rewriting using LLM (resolves pronouns like "that", "it")
✅ Grounded answers with inline citations: [msg: m_9b2] / [msg: m_9b2, page: 2]
✅ FastAPI backend + Streamlit UI with debug panel
✅ Per-turn JSONL trace logs
✅ Docker-compose ready
Setup1. Install dependenciesbashpip install -r requirements.txt2. Get a free Groq API keySign up at https://console.groq.com → create API key → create a .env file:bashecho 'GROQ_API_KEY=your_key_here' > .env3. Create sample datasetbashpython create_sample_data.pyThis creates 8 emails across 3 threads with 4 PDF attachments in data/raw/.4. Build the indexbashpython ingest.pyProduces data/processed/chunks.json, bm25.pkl, and threads.json.5. RunOption A — Local (two terminals):bash# Terminal 1: API
uvicorn api:app --reload --port 8000

# Terminal 2: UI
streamlit run app.pyOpen http://localhost:8501Option B — Docker:bashexport GROQ_API_KEY="your_key_here"
docker compose up --buildAPI EndpointsMethodPathBodyPOST/start_session{"thread_id": "T-0001"}POST/ask{"session_id": "...", "text": "...", "search_outside_thread": false}POST/switch_thread{"session_id": "...", "thread_id": "..."}POST/reset_session{"session_id": "..."}GET/threadsList all available threadsArchitecture[.eml files + PDFs]
       ↓
   ingest.py  →  chunks.json + bm25.pkl + threads.json
       ↓
[Streamlit UI] ⟷ [FastAPI] → [Retriever → Rewriter → Answerer (Groq llama-3.1-8b)]
                                        ↓
                                  trace.jsonlPipeline per query:
Rewrite — Query is rewritten to be standalone using last 5 turns + tracked entities (Groq LLM)
Retrieve — BM25 search over chunks, filtered to active thread
Answer — Strict-prompt LLM call with evidence + citation rules
Log — Full trace appended to runs/<timestamp>/trace.jsonl
Design Choices
BM25 over vectors: Assignment baseline. Emails contain specific terms (names, amounts, dates) where lexical search excels. Easily extensible to vector search via late fusion.
Subject-based threading fallback: In-Reply-To header is primary; subject normalization (stripping Re:/Fwd:) is the fallback.
One chunk per email body: Emails are short and self-contained — no need to split.
Page-aware PDF chunking: Each PDF page → text → 300-token chunks (50 overlap). This preserves the page number for citations.
LLM rewriter over rule-based: Pronoun resolution via Groq is more reliable than regex rules.
Strict citation prompt: Forces the model to cite every claim or refuse to answer (graceful failure).
Streamlit + FastAPI separation: API exposes the 4 required endpoints; Streamlit calls them. Clean boundary for future frontend swap.
Known Limitations
BM25 misses semantic matches (e.g., "approval" vs "sign-off"). Vector search would help — easy to add.
Subject-based threading fails if subjects are reused; In-Reply-To covers most real cases.
No OCR for scanned PDFs (only text-based PDFs).
In-memory sessions — server restart loses session state.
Performance
Lexical-only path: ~1.5–2.5s per turn (warm cache, top-k=8)
Latency dominated by Groq LLM call (~800ms–1.5s); BM25 is sub-50ms
Logged in every trace record under latency_ms
TestingSee sample_questions.md for 7 sample questions covering: factual lookup, pronoun resolution, ellipsis, correction, comparison, timeline, and graceful failure.File StructureFilePurposecreate_sample_data.pyGenerates synthetic dataset (.eml + PDFs)ingest.pyParses emails, builds BM25 indexcore/retriever.pyBM25 search with thread filtercore/memory.pySession memory + entity extractioncore/rewriter.pyQuery rewriting via Groqcore/answerer.pyGrounded answer generation with citation parsingapi.pyFastAPI endpointsapp.pyStreamlit UIruns/<ts>/trace.jsonlPer-turn execution logsTech Stack
Backend: FastAPI + Uvicorn
UI: Streamlit
Retrieval: rank-bm25 (pure Python BM25)
LLM: Groq API (llama-3.1-8b-instant)
Document parsing: PyMuPDF (PDFs), python-docx (DOCX), BeautifulSoup4 (HTML)
Containerization: Docker + docker-compose
