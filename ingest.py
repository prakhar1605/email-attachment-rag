"""
Ingest emails and attachments. Build BM25 index.
Run: python ingest.py
"""
import os
import json
import pickle
import re
from email import policy
from email.parser import BytesParser
from datetime import datetime
import fitz  # pymupdf
from docx import Document
from bs4 import BeautifulSoup
from rank_bm25 import BM25Okapi


CHUNKS_PATH = "data/processed/chunks.json"
BM25_PATH = "data/processed/bm25.pkl"
THREADS_PATH = "data/processed/threads.json"
EML_DIR = "data/raw"


def normalize_subject(subject):
    """Strip Re:/Fwd: for thread grouping fallback."""
    if not subject:
        return ""
    s = subject.strip()
    while True:
        new = re.sub(r'^(Re|Fwd|FW|RE|FWD):\s*', '', s, flags=re.IGNORECASE)
        if new == s:
            break
        s = new
    return s.strip().lower()


def chunk_text(text, chunk_size=300, overlap=50):
    """Word-based chunking for attachments."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks


def extract_pdf_pages(filepath):
    """Returns list of (page_no, text) tuples."""
    pages = []
    with fitz.open(filepath) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if text:
                pages.append((i, text))
    return pages


def extract_docx_text(filepath):
    doc = Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_html_text(content):
    return BeautifulSoup(content, "html.parser").get_text(separator="\n").strip()


def parse_eml(filepath):
    """Parse .eml file and return metadata + body + attachments."""
    with open(filepath, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    msg_id = msg.get("Message-ID", "").strip("<>").split("@")[0]
    in_reply_to = msg.get("In-Reply-To", "").strip("<>").split("@")[0] if msg.get("In-Reply-To") else None
    references = msg.get("References", "")
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    to = msg.get("To", "")
    cc = msg.get("Cc", "")
    date = msg.get("Date", "")

    # Extract body
    body = ""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    body += part.get_content()
                except Exception:
                    body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            elif "attachment" in disp:
                fname = part.get_filename()
                if fname:
                    attachments.append({
                        "filename": fname,
                        "content": part.get_payload(decode=True),
                        "content_type": ctype
                    })
    else:
        body = msg.get_content() if hasattr(msg, "get_content") else msg.get_payload()

    return {
        "message_id": msg_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "subject": subject,
        "from": sender,
        "to": to,
        "cc": cc,
        "date": date,
        "body": body.strip(),
        "attachments": attachments
    }


def build_threads(emails):
    """Group emails into threads using In-Reply-To, then subject."""
    msg_to_thread = {}
    threads = {}
    next_id = 1

    # Sort by date for stable assignment
    def parse_date(d):
        try:
            return datetime.strptime(d[:25], "%a, %d %b %Y %H:%M:%S")
        except Exception:
            return datetime.min

    emails_sorted = sorted(emails, key=lambda e: parse_date(e["date"]))

    for em in emails_sorted:
        mid = em["message_id"]
        parent = em["in_reply_to"]

        if parent and parent in msg_to_thread:
            tid = msg_to_thread[parent]
        else:
            # Try subject normalization
            norm = normalize_subject(em["subject"])
            tid = None
            for existing_tid, info in threads.items():
                if info["norm_subject"] == norm and norm:
                    tid = existing_tid
                    break
            if tid is None:
                tid = f"T-{next_id:04d}"
                next_id += 1
                threads[tid] = {
                    "thread_id": tid,
                    "norm_subject": norm,
                    "subject": em["subject"],
                    "messages": []
                }

        msg_to_thread[mid] = tid
        threads[tid]["messages"].append(mid)

    return threads, msg_to_thread


def main():
    os.makedirs("data/processed", exist_ok=True)

    # Parse all emails
    emails = []
    for fn in sorted(os.listdir(EML_DIR)):
        if fn.endswith(".eml"):
            path = os.path.join(EML_DIR, fn)
            try:
                em = parse_eml(path)
                emails.append(em)
                print(f"  parsed {fn}: msg_id={em['message_id']}")
            except Exception as e:
                print(f"  error parsing {fn}: {e}")

    print(f"\nTotal emails parsed: {len(emails)}")

    # Build threads
    threads, msg_to_thread = build_threads(emails)
    print(f"Total threads: {len(threads)}")

    # Build chunks
    chunks = []
    chunk_id = 1

    for em in emails:
        tid = msg_to_thread[em["message_id"]]

        # Email body chunk
        if em["body"]:
            chunks.append({
                "chunk_id": f"c_{chunk_id:04d}",
                "thread_id": tid,
                "message_id": em["message_id"],
                "doc_id": em["message_id"],
                "type": "email",
                "page_no": None,
                "text": f"Subject: {em['subject']}\nFrom: {em['from']}\nTo: {em['to']}\nDate: {em['date']}\n\n{em['body']}",
                "subject": em["subject"],
                "from": em["from"],
                "to": em["to"],
                "date": em["date"]
            })
            chunk_id += 1

        # Attachment chunks
        for att in em["attachments"]:
            fname = att["filename"]
            ctype = att["content_type"]
            content = att["content"]

            # Save attachment temporarily
            tmp_path = f"data/processed/_tmp_{fname}"
            with open(tmp_path, "wb") as f:
                f.write(content)

            try:
                if fname.lower().endswith(".pdf"):
                    pages = extract_pdf_pages(tmp_path)
                    for page_no, page_text in pages:
                        sub_chunks = chunk_text(page_text, 300, 50)
                        for sc in sub_chunks:
                            chunks.append({
                                "chunk_id": f"c_{chunk_id:04d}",
                                "thread_id": tid,
                                "message_id": em["message_id"],
                                "doc_id": f"{em['message_id']}_{fname}",
                                "type": "pdf",
                                "page_no": page_no,
                                "text": sc,
                                "filename": fname,
                                "subject": em["subject"],
                                "from": em["from"],
                                "date": em["date"]
                            })
                            chunk_id += 1

                elif fname.lower().endswith(".docx"):
                    text = extract_docx_text(tmp_path)
                    sub_chunks = chunk_text(text, 300, 50)
                    for sc in sub_chunks:
                        chunks.append({
                            "chunk_id": f"c_{chunk_id:04d}",
                            "thread_id": tid,
                            "message_id": em["message_id"],
                            "doc_id": f"{em['message_id']}_{fname}",
                            "type": "docx",
                            "page_no": None,
                            "text": sc,
                            "filename": fname,
                            "subject": em["subject"],
                            "from": em["from"],
                            "date": em["date"]
                        })
                        chunk_id += 1

                elif fname.lower().endswith((".txt", ".html", ".htm")):
                    raw = content.decode("utf-8", errors="ignore")
                    if fname.lower().endswith((".html", ".htm")):
                        raw = extract_html_text(raw)
                    sub_chunks = chunk_text(raw, 300, 50)
                    for sc in sub_chunks:
                        chunks.append({
                            "chunk_id": f"c_{chunk_id:04d}",
                            "thread_id": tid,
                            "message_id": em["message_id"],
                            "doc_id": f"{em['message_id']}_{fname}",
                            "type": "txt",
                            "page_no": None,
                            "text": sc,
                            "filename": fname,
                            "subject": em["subject"],
                            "from": em["from"],
                            "date": em["date"]
                        })
                        chunk_id += 1
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    print(f"Total chunks: {len(chunks)}")

    # Save chunks
    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks, f, indent=2, default=str)

    # Save threads
    with open(THREADS_PATH, "w") as f:
        json.dump(threads, f, indent=2)

    # Build BM25
    tokenized = [c["text"].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "chunk_ids": [c["chunk_id"] for c in chunks]}, f)

    print(f"\n✓ Saved {CHUNKS_PATH}")
    print(f"✓ Saved {THREADS_PATH}")
    print(f"✓ Saved {BM25_PATH}")


if __name__ == "__main__":
    main()