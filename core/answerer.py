"""Answer generator with grounded citations."""
import os
import re
from dotenv import load_dotenv
load_dotenv()
from groq import Groq


def build_evidence_block(retrieved):
    """Format retrieved chunks as evidence."""
    lines = []
    for i, r in enumerate(retrieved, 1):
        c = r["chunk"]
        if c["type"] == "email":
            lines.append(
                f"[E{i}] type=email, msg={c['message_id']}, date={c.get('date','')}\n"
                f"From: {c.get('from','')}\nSubject: {c.get('subject','')}\n"
                f"Content: {c['text'][:1000]}"
            )
        elif c["type"] == "pdf":
            lines.append(
                f"[E{i}] type=pdf, msg={c['message_id']}, page={c['page_no']}, "
                f"file={c.get('filename','')}\n"
                f"Content: {c['text'][:1000]}"
            )
        else:
            lines.append(
                f"[E{i}] type={c['type']}, msg={c['message_id']}, "
                f"file={c.get('filename','')}\n"
                f"Content: {c['text'][:1000]}"
            )
    return "\n\n".join(lines)


def parse_citations(answer_text):
    """Extract citations from answer text."""
    citations = []
    # Pattern: [msg: m_xxx, page: N]
    pdf_pattern = r'\[msg:\s*([\w_]+),\s*page:\s*(\d+)\]'
    for m in re.finditer(pdf_pattern, answer_text):
        citations.append({
            "type": "pdf",
            "message_id": m.group(1),
            "page": int(m.group(2))
        })
    # Pattern: [msg: m_xxx]
    email_pattern = r'\[msg:\s*([\w_]+)\](?!\s*,\s*page)'
    for m in re.finditer(email_pattern, answer_text):
        before = answer_text[:m.start()]
        if not re.search(r'\[msg:\s*' + m.group(1) + r',\s*page:\s*\d+\]\s*$', before):
            citations.append({
                "type": "email",
                "message_id": m.group(1)
            })
    return citations


def generate_answer(rewritten_query, retrieved, memory, client=None):
    """Generate grounded answer with citations."""
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    if not retrieved:
        return {
            "answer": "I don't have enough information in this thread to answer that. Could you ask something more specific or try toggling 'search outside thread'?",
            "citations": [],
            "used_chunk_ids": []
        }

    evidence = build_evidence_block(retrieved)
    context = memory.get_context()

    prompt = f"""You answer questions about an email thread using ONLY the evidence below.

CITATION RULES (CRITICAL):
- For email facts: cite as [msg: <message_id>]
- For PDF facts: cite as [msg: <message_id>, page: <n>]
- Every factual claim MUST have a citation right after it
- Do NOT make up facts not in the evidence
- If evidence is insufficient, say "I don't have enough information about this in the thread" and suggest one clarifying question

EVIDENCE:
{evidence}

{context}

QUESTION: {rewritten_query}

Provide a concise answer with inline citations:"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500
    )
    answer = resp.choices[0].message.content.strip()
    citations = parse_citations(answer)

    # Determine which chunks were used
    cited_msgs = set(c["message_id"] for c in citations)
    used = [r["chunk_id"] for r in retrieved if r["chunk"]["message_id"] in cited_msgs]

    return {
        "answer": answer,
        "citations": citations,
        "used_chunk_ids": used,
        "tokens": resp.usage.total_tokens if resp.usage else 0
    }