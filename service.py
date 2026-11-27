"""Ties storage, chunking, retrieval and generation together (no Flask here, so it is easy to test)."""
from .chunker import chunk_text
from .retriever import TfidfRetriever

NOT_FOUND = "I couldn't find this in the uploaded documents."


class RagService:
    def __init__(self, storage, llm, chunk_words=100, overlap=25):
        self.storage = storage
        self.llm = llm
        self.chunk_words = chunk_words
        self.overlap = overlap
        self.retriever = TfidfRetriever([])
        self.rebuild()

    def rebuild(self):
        chunks = []
        for name in self.storage.list_names():
            chunks.extend(chunk_text(self.storage.read(name), name, self.chunk_words, self.overlap))
        self.retriever = TfidfRetriever(chunks)  # swapped in one step, so readers never see a half-built index
        return len(chunks)

    def documents(self):
        counts = {}
        for chunk in self.retriever.chunks:
            counts[chunk.source] = counts.get(chunk.source, 0) + 1
        return [{"name": n, "chunks": counts.get(n, 0)} for n in self.storage.list_names()]

    def add_document(self, name, text):
        self.storage.write(name, text)
        return self.rebuild()

    def ask(self, question, top_k=3):
        hits = self.retriever.search(question, top_k=top_k)
        if not hits:
            # No relevant passage: skip the model call entirely (cheaper, and avoids made-up answers).
            return {"answer": NOT_FOUND, "sources": [], "used_llm": False}
        answer = self.llm.generate(question, hits)
        sources = [
            {"ref": i, "source": c.source, "chunk": c.index, "score": round(s, 3), "snippet": c.text[:200]}
            for i, (c, s) in enumerate(hits, start=1)
        ]
        return {"answer": answer, "sources": sources, "used_llm": True}
