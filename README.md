# Dispatch (Agent Nexus)

Dispatch is a local-first orchestration system for AI task workflows.

## What Is Active

- `backend/`:
  - FastAPI service (`main.py`)
  - SQLite data store (`backend/agent_tasks.db`)
  - REST + SSE endpoints
- `frontend-nextjs/`:
  - Next.js + Tabler dashboard
  - Cookie-based auth bridge (`src/app/api/auth/*`)
  - Backend proxy (`src/app/api/dispatch/[...path]/route.ts`)

## Current Workflow States

`backlog -> todo -> planning -> hitl_review -> working -> ready_to_implement -> approval -> completed`

Additional state: `blocked`.

## Quick Start

### 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Backend runs at `http://localhost:8000` by default.

### 2) Frontend (Next.js)

```bash
cd frontend-nextjs
npm install
npm run dev
```

Frontend runs at `http://localhost:3001`.

## Authentication Model

- Login through `frontend-nextjs` (`/login`).
- Frontend stores a signed session cookie.
- Frontend proxy injects:
  - `X-Actor-Id`
  - `X-Actor-Role`
  - `X-API-Token` (if configured)

## Project Scope

The UI is currently scoped to the **Pesulabs** project for day-to-day usage.

## Repository Structure

```text
Dispatch/
├── backend/                 # Active backend API
├── frontend-nextjs/         # Active frontend UI
├── docs/                    # Documentation
├── scripts/                 # Ops/testing scripts
├── agents/                  # Agent profiles/config
├── frontend/                # Legacy static frontend (kept for reference)
└── tests/                   # Python tests
```

## Documentation

Start here:

- `docs/README.md` (documentation index)
- `docs/API.md` (backend endpoints)
- `docs/FRONTEND_USER_INTEGRATION.md` (frontend integration contract)
- `docs/CLI.md` (legacy CLI notes)

## Notes

- `frontend/` is legacy and not the primary UI anymore.
- There are generated/diagnostic files in `backend/` and root; do not use them as source of truth over `backend/main.py` and `frontend-nextjs/src/`.
