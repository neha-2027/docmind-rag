"""Flask API for DocuMind: ask questions about your own documents (RAG)."""
import logging

from flask import Flask, jsonify, request

from rag.llm import make_llm
from rag.service import RagService
from rag.storage import make_storage, safe_name

MAX_QUESTION_CHARS = 500
MAX_DOC_CHARS = 200_000
log = logging.getLogger("docmind")


def create_app(service=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # reject huge request bodies
    svc = service or RagService(make_storage(), make_llm())

    def error(message, status):
        return jsonify({"error": message}), status

    @app.errorhandler(404)
    def not_found(_e):
        return error("resource not found", 404)

    @app.errorhandler(413)
    def too_large(_e):
        return error("request body too large", 413)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/documents")
    def documents():
        return jsonify({"documents": svc.documents()})

    @app.post("/documents")
    def add_document():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("send JSON with 'name' and 'text'", 400)
        try:
            name = safe_name(data.get("name"))
        except ValueError as exc:
            return error(str(exc), 400)
        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            return error("'text' must be a non-empty string", 400)
        if len(text) > MAX_DOC_CHARS:
            return error(f"'text' is longer than {MAX_DOC_CHARS} characters", 400)
        chunks = svc.add_document(name, text)
        return jsonify({"name": name, "total_chunks": chunks}), 201

    @app.post("/ask")
    def ask():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("send JSON with 'question'", 400)
        question = data.get("question")
        if not isinstance(question, str) or not question.strip():
            return error("'question' must be a non-empty string", 400)
        if len(question) > MAX_QUESTION_CHARS:
            return error(f"'question' is longer than {MAX_QUESTION_CHARS} characters", 400)
        top_k = data.get("top_k", 3)
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 10:
            return error("'top_k' must be an integer from 1 to 10", 400)
        try:
            return jsonify(svc.ask(question.strip(), top_k=top_k))
        except Exception:  # model/network failure: log details, do not leak them to the client
            log.exception("answer generation failed")
            return error("answer generation failed", 502)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
