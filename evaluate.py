"""Measure retrieval quality on a small labelled question set.

For each question we check whether the document that should contain the answer appears in the
top-k retrieved chunks (hit@k). Run:  python evaluate.py
"""
import json
import sys

from rag.chunker import chunk_text
from rag.retriever import TfidfRetriever
from rag.storage import LocalStorage


def evaluate(docs_dir="sample_docs", eval_path="eval_set.json", ks=(1, 3)):
    storage = LocalStorage(docs_dir)
    chunks = []
    for name in storage.list_names():
        chunks.extend(chunk_text(storage.read(name), name))
    retriever = TfidfRetriever(chunks)
    with open(eval_path, encoding="utf-8") as f:
        cases = json.load(f)

    results = {k: 0 for k in ks}
    misses = []
    for case in cases:
        # min_score=0 so we measure ranking quality, not the "not found" threshold
        ranked = [c.source for c, _ in retriever.search(case["question"], top_k=max(ks), min_score=0.0)]
        for k in ks:
            if case["expected_source"] in ranked[:k]:
                results[k] += 1
        if case["expected_source"] not in ranked[:1]:
            misses.append((case["question"], case["expected_source"], ranked[:1]))
    return len(cases), results, misses


if __name__ == "__main__":
    total, results, misses = evaluate()
    print(f"Questions: {total}")
    for k, hits in results.items():
        print(f"hit@{k}: {hits}/{total} = {100 * hits / total:.1f}%")
    for question, expected, got in misses:
        print(f"  top-1 miss: {question!r} expected {expected}, got {got}")
    sys.exit(0)
