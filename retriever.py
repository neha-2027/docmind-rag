"""TF-IDF retriever. Swap this class for an embedding + vector-store retriever later;
the rest of the app only relies on `search(query, top_k, min_score)`."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfRetriever:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self._vectorizer = None
        self._matrix = None
        if self.chunks:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
            try:
                self._matrix = vectorizer.fit_transform([c.text for c in self.chunks])
                self._vectorizer = vectorizer
            except ValueError:  # e.g. documents contain only stop words
                self._matrix = None

    def search(self, query, top_k=3, min_score=0.08):
        """Return up to top_k (chunk, score) pairs, best first, ignoring weak matches."""
        if self._matrix is None or not query or not query.strip():
            return []
        scores = cosine_similarity(self._vectorizer.transform([query]), self._matrix)[0]
        order = scores.argsort()[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in order if scores[i] >= min_score]
