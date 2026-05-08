"""FastAPI endpoints."""
import os
from dotenv import load_dotenv
load_dotenv()
import json
import uuid
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.retriever import Retriever
from core.memory import SessionMemory
from core.rewriter import rewrite_query
from core.answerer import generate_answer

app = FastAPI(title="Email RAG API")

# Globals
retriever = None
sessions = {}
RUN_DIR = f"runs/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(RUN_DIR, exist_ok=True)
TRACE_FILE = f"{RUN_DIR}/trace.jsonl"


def get_retriever():
    global retriever
    if retriever is None:
        retriever = Retriever()
    return retriever


class StartSessionRequest(BaseModel):
    thread_id: str


class AskRequest(BaseModel):
    session_id: str
    text: str
    search_outside_thread: bool = False


class SwitchThreadRequest(BaseModel):
    session_id: str
    thread_id: str


class ResetRequest(BaseModel):
    session_id: str


@app.post("/start_session")
def start_session(req: StartSessionRequest):
    sid = str(uuid.uuid4())[:8]
    sessions[sid] = SessionMemory(thread_id=req.thread_id)
    return {"session_id": sid, "thread_id": req.thread_id}


@app.post("/ask")
def ask(req: AskRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found")
    memory = sessions[req.session_id]
    r = get_retriever()
    t0 = time.time()

    # Step 1: Rewrite
    rewritten = rewrite_query(req.text, memory)

    # Step 2: Retrieve
    retrieved = r.search(
        rewritten,
        thread_id=memory.thread_id,
        top_k=8,
        search_outside=req.search_outside_thread
    )

    # Step 3: Answer
    result = generate_answer(rewritten, retrieved, memory)

    # Step 4: Update memory
    memory.add_turn(req.text, result["answer"], result["citations"])

    latency_ms = int((time.time() - t0) * 1000)
    trace_id = str(uuid.uuid4())[:8]

    # Step 5: Log trace
    trace = {
        "trace_id": trace_id,
        "timestamp": datetime.now().isoformat(),
        "session_id": req.session_id,
        "thread_id": memory.thread_id,
        "user_text": req.text,
        "rewrite": rewritten,
        "retrieved": [{"chunk_id": x["chunk_id"], "score": x["score"]} for x in retrieved],
        "used_chunk_ids": result["used_chunk_ids"],
        "answer": result["answer"],
        "citations": result["citations"],
        "latency_ms": latency_ms,
        "tokens": result.get("tokens", 0),
        "search_outside_thread": req.search_outside_thread
    }
    with open(TRACE_FILE, "a") as f:
        f.write(json.dumps(trace) + "\n")

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "rewrite": rewritten,
        "retrieved": [{"chunk_id": x["chunk_id"], "score": x["score"],
                       "type": x["chunk"]["type"],
                       "message_id": x["chunk"]["message_id"],
                       "page_no": x["chunk"].get("page_no")}
                      for x in retrieved],
        "trace_id": trace_id,
        "latency_ms": latency_ms
    }


@app.post("/switch_thread")
def switch_thread(req: SwitchThreadRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found")
    sessions[req.session_id].thread_id = req.thread_id
    sessions[req.session_id].reset()
    return {"session_id": req.session_id, "thread_id": req.thread_id}


@app.post("/reset_session")
def reset_session(req: ResetRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found")
    sessions[req.session_id].reset()
    return {"session_id": req.session_id, "status": "reset"}


@app.get("/threads")
def list_threads():
    with open("data/processed/threads.json") as f:
        threads = json.load(f)
    return {"threads": [{"thread_id": t, "subject": info["subject"],
                          "messages": len(info["messages"])}
                         for t, info in threads.items()]}


@app.get("/health")
def health():
    return {"status": "ok"}