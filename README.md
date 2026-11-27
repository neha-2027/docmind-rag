# DocuMind: Retrieval-Augmented Generation (RAG) over your own documents

Ask questions about your notes and documents and get answers that **cite the passages they came from**.
Built with **Python, Flask, scikit-learn, the Claude API (Anthropic) and Amazon S3**, packaged with Docker.

## How it works
```
documents (local folder or S3)
   -> chunking (overlapping word windows)
   -> TF-IDF index
question -> retrieve top-k passages -> (no relevant passage? answer "not found", no model call)
         -> prompt = system rules + numbered passages + question -> Claude -> answer with [1], [2] citations
```
- **Grounding:** the system prompt tells the model to answer only from the numbered passages, cite them, and say when the answer is missing. Passages are treated as untrusted data (a basic defence against prompt injection from uploaded text).
- **Cost and hallucination control:** if retrieval finds nothing relevant, the model is not called at all.
- **Works offline:** with no `ANTHROPIC_API_KEY`, an extractive fallback returns the most relevant sentences, so you can run and test everything for free.
- **Cloud-ready storage:** set `S3_BUCKET` and documents are read from and written to Amazon S3 using the standard AWS credential chain (an IAM role on AWS, no hard-coded keys).
- **Swappable retriever:** `TfidfRetriever` can be replaced with an embedding model + vector store; the rest of the app only calls `search()`.

## Run locally
```bash
git clone <your-repo-url>
cd docmind-rag
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # open http://127.0.0.1:5000  (uses sample_docs/)
```
To use Claude for answers, set your key first (never commit it):
```bash
export ANTHROPIC_API_KEY="your-key"       # Windows PowerShell: $env:ANTHROPIC_API_KEY="your-key"
export CLAUDE_MODEL="<model name from Anthropic's docs>"   # optional
```

## Run with Docker
```bash
docker build -t docmind .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY="your-key" docmind
```

## Use S3 for documents
```bash
export S3_BUCKET="my-docmind-bucket"   # optional: S3_PREFIX (default "docs/")
```
The app needs only `s3:ListBucket` on the bucket and `s3:GetObject` / `s3:PutObject` on `docs/*`. Attach those to an IAM role for the compute service you deploy on (EC2, ECS, App Runner, etc.).

## API
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | `{"question": "...", "top_k": 3}` returns `answer`, `sources`, `used_llm` |
| GET | `/documents` | List documents and chunk counts |
| POST | `/documents` | `{"name": "notes.md", "text": "..."}` adds a document and re-indexes |
| GET | `/health` | Health check |

## Tests and evaluation
```bash
python -m unittest discover -v   # 22 tests
python evaluate.py               # retrieval hit@1 / hit@3 on eval_set.json
```
Tests use fakes for the Claude client and for S3, so they run offline.
`evaluate.py` measures whether the right document appears in the top-k results.
On the 12 questions in `eval_set.json` (written against the 6 small sample documents) it scores 12/12 at both k=1 and k=3.
That set is small and easy, so treat it as a regression check, not as a general accuracy claim. Add harder questions of your own.

## Security notes
- Uploaded file names are validated (no paths, only `.txt` / `.md`), and request sizes are limited.
- API keys come from environment variables only.
- Model errors are logged server-side and return a generic 502 to the client.

## Limitations and next steps
- TF-IDF matches words, not meaning; "automobile" will not match "car". Next step: embeddings (for example a sentence-transformers model) plus a vector store such as FAISS or pgvector.
- Only `.txt` and `.md`; PDF support (for example `pypdf`) is a good next step.
- No authentication; add it before exposing the service publicly (an open endpoint with your API key can be used to run up costs).
- The index is held in memory and rebuilt on start-up and after uploads.
