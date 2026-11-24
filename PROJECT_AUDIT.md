# Project audit

## Implemented in scaffold

- Separate FastAPI backend and React/Vite frontend.
- SQLAlchemy 2 entities and Alembic initial migration for users, documents, chunks, conversations, and messages.
- PostgreSQL UUID keys, cascading ownership relationships, pgvector `Vector(768)`, and HNSW cosine index.
- bcrypt password hashing and expiring JWT auth; user ownership filters protect document and conversation operations.
- PDF/TXT/DOCX extraction, filename extension validation, empty-content handling, and configurable byte limit.
- Chunking with overlap; Gemini embedding REST request validates 768 dimensions; indexed chunks persist in the same DB transaction as document metadata.
- Cosine nearest-neighbor retrieval scoped to the authenticated user and optionally to selected documents.
- Gemini grounded answer, summary, semantic search, comparison, and source metadata with chunk references (PDF page labels are retained as text and may be surfaced in citations only when retrieval chunk metadata has a page number).
- Frontend auth, dashboard, upload/library/delete, extracted text view, summary, chat scope, source chips, and document comparison.
- README, `.env.example`, `.gitignore`, Docker Compose pgvector database, and focused backend unit tests.

## Checks performed

- Python source compilation (`python3 -m compileall`): passed.
- Python application import check: not completed; this environment does not have FastAPI installed (`ModuleNotFoundError`).
- Frontend dependency/build check: not completed; dependency installation produced no output in the restricted environment and was stopped, so Vite is unavailable.
- Pytest suite: not run; backend dependencies are not installed in this environment.
- PostgreSQL connection/migration application: not run; requires a local PostgreSQL service.
- Gemini embedding/generation and end-to-end RAG: not run; requires `GEMINI_API_KEY` and network access.
- Browser-based workflow: not run.

## Known limits / follow-up

- PDF and DOCX extraction is text-based; scanned PDFs need OCR and DOCX pagination is not reliably represented. Chunks are cited by chunk number when page metadata is unavailable.
- Embeddings are requested one chunk at a time, which is simple but can be slow and costly for large uploads. Add Gemini batching, retry/backoff, and background jobs for production scale.
- Upload handling reads up to configured limit into memory. Document text is kept in PostgreSQL; no original binary is retained.
- There is no conversation delete/rename endpoint, password reset, email verification, or rate limiting.
- PostgreSQL and Gemini behavior remains unverified until provisioned and exercised; the unit tests do not claim those integrations.
