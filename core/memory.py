"""Session memory with entity tracking."""
import re
from collections import defaultdict


class SessionMemory:
    def __init__(self, thread_id=None):
        self.thread_id = thread_id
        self.turns = []  # list of {"user": ..., "assistant": ..., "citations": [...]}
        self.entities = {
            "people": set(),
            "dates": set(),
            "amounts": set(),
            "filenames": set()
        }

    def add_turn(self, user_text, assistant_text, citations=None):
        self.turns.append({
            "user": user_text,
            "assistant": assistant_text,
            "citations": citations or []
        })
        # Keep last 5 turns
        if len(self.turns) > 5:
            self.turns = self.turns[-5:]
        self._extract_entities(user_text + " " + assistant_text)

    def _extract_entities(self, text):
        # Dates: YYYY-MM-DD or "May 12, 2001" etc.
        for m in re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text):
            self.entities["dates"].add(m)
        for m in re.findall(
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b',
            text):
            self.entities["dates"].add(m)

        # Amounts: $X,XXX
        for m in re.findall(r'\$[\d,]+(?:\.\d+)?', text):
            self.entities["amounts"].add(m)

        # Filenames
        for m in re.findall(r'\b[\w\-]+\.(?:pdf|docx?|txt|html?)\b', text, re.IGNORECASE):
            self.entities["filenames"].add(m)

    def get_context(self):
        """Returns formatted context for LLM."""
        lines = []
        if self.turns:
            lines.append("RECENT CONVERSATION:")
            for i, t in enumerate(self.turns[-3:], 1):
                lines.append(f"User: {t['user']}")
                lines.append(f"Assistant: {t['assistant']}")
            lines.append("")
        if any(self.entities.values()):
            lines.append("KNOWN ENTITIES:")
            for k, v in self.entities.items():
                if v:
                    lines.append(f"  {k}: {', '.join(list(v)[:5])}")
        return "\n".join(lines)

    def reset(self):
        self.turns = []
        self.entities = {k: set() for k in self.entities}

    def to_dict(self):
        return {
            "thread_id": self.thread_id,
            "turns": self.turns,
            "entities": {k: list(v) for k, v in self.entities.items()}
        }