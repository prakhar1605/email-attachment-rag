"""BM25 retriever with thread filtering."""
import json
import pickle


class Retriever:
    def __init__(self, chunks_path="data/processed/chunks.json",
                 bm25_path="data/processed/bm25.pkl"):
        with open(chunks_path) as f:
            self.chunks = json.load(f)
        with open(bm25_path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.chunk_ids = data["chunk_ids"]
        self.id_to_chunk = {c["chunk_id"]: c for c in self.chunks}

    def search(self, query, thread_id=None, top_k=8, search_outside=False):
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)

        # Pair scores with chunks
        scored = []
        for cid, score in zip(self.chunk_ids, scores):
            chunk = self.id_to_chunk[cid]
            if not search_outside and thread_id and chunk["thread_id"] != thread_id:
                continue
            scored.append((score, chunk))

        # Sort by score, return top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk in scored[:top_k]:
            if score > 0:
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "score": float(score),
                    "chunk": chunk
                })
        return results