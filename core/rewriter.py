"""Query rewriter using Groq LLM."""
import os
from dotenv import load_dotenv
load_dotenv()
from groq import Groq


def rewrite_query(user_text, memory, client=None):
    """Rewrites user question to be standalone using memory."""
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    context = memory.get_context()

    # If no history, no need to rewrite
    if not memory.turns:
        return user_text

    prompt = f"""You are a query rewriter. Given conversation history and a new user question, rewrite the question to be standalone (no pronouns like "that", "it", "this"; no ellipsis).

{context}

New user question: {user_text}

Rules:
- Output ONLY the rewritten question, no explanation
- Keep it concise
- If the question is already standalone, output it unchanged
- Resolve pronouns using context

Rewritten question:"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        rewritten = resp.choices[0].message.content.strip()
        # Clean up if model adds quotes or labels
        rewritten = rewritten.strip('"\'').strip()
        if rewritten.lower().startswith("rewritten question:"):
            rewritten = rewritten.split(":", 1)[1].strip()
        return rewritten if rewritten else user_text
    except Exception as e:
        print(f"Rewrite error: {e}")
        return user_text