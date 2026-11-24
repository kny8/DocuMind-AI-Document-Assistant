# DocuMind – AI Document Intelligence

DocuMind is a full-stack document workspace with private user accounts, PDF/TXT/DOCX ingestion, Gemini embeddings, pgvector semantic retrieval, and grounded question answering. Backend and frontend are separate applications.

## Features

- FastAPI REST API with SQLAlchemy 2, PostgreSQL, pgvector, Alembic, Pydantic, bcrypt, and JWT.
- Registration/login, protected routes, and ownership checks for documents and conversations.
- Upload, extract, list, inspect, summarize, and delete PDF, TXT, and DOCX documents (20 MB default limit).
- Gemini REST text generation and 768-dimensional `gemini-embedding-001` embeddings.
- Overlapping text chunks persisted with vector embeddings and HNSW cosine index.
- Search over all documents or a selected set; chat answers cite filename and page or chunk references and are prompted to abstain when context lacks an answer.
- Cross-document comparison and individual document summaries.
- React/Vite/Tailwind responsive UI for auth, dashboard, library, document detail, chat, and comparison.
- FastAPI Swagger UI at `/docs`.

## Requirements

- Python 3.11+
- Node.js 20+
- Docker (for the included PostgreSQL + pgvector service) or a PostgreSQL server with pgvector installed
- A Gemini API key for indexing and AI features

## Run locally

1. Copy `.env.example` to `.env`. Set a long random `JWT_SECRET` and `GEMINI_API_KEY`.
2. Start the database: `docker compose up -d db`. The example DB URL uses `documind` / `change-me`; set `POSTGRES_PASSWORD` consistently before first startup if changing it.
3. Install/run backend:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

4. Install/run frontend in another terminal:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open `http://localhost:5173`. API Swagger is at `http://localhost:8000/docs`. To use a different API origin, set `VITE_API_URL` (for example `http://localhost:8000/api`) in the frontend environment.

## REST API

All routes except `/health` and auth registration/login require `Authorization: Bearer <JWT>`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register`, `/api/auth/login` | Create account / obtain token |
| GET | `/api/auth/me` | Current account |
| GET/POST | `/api/documents` | List / upload and index |
| GET/DELETE | `/api/documents/{id}` | Inspect metadata / delete |
| GET | `/api/documents/{id}/text` | Read extracted text |
| POST | `/api/documents/{id}/summary` | Gemini summary |
| POST | `/api/search` | Semantic search, optional document IDs |
| POST | `/api/compare` | Compare 2–10 selected documents |
| POST/GET | `/api/conversations` | Create/list conversations |
| GET/POST | `/api/conversations/{id}/messages` | Read/send RAG messages |

Request and response schemas are documented in Swagger. Upload uses multipart form field `file`; chat takes `{ "question": "...", "document_ids": ["..."] }`, where omitted/null IDs means all owned documents.

## Tests and verification

From `backend/`, run `pytest`. The current tests cover password hashing and chunk splitting only. Database behavior, Alembic application, Gemini REST calls, and end-to-end RAG require local PostgreSQL, credentials, and service access; see [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for verified and outstanding checks.

## Security notes

Keep `.env` private. Change the example database password and development JWT secret before use beyond local development. Uploaded file bytes are processed in memory and are not retained; extracted text and embeddings are stored in PostgreSQL. Add rate limiting, account recovery, and production secret management before public deployment.
