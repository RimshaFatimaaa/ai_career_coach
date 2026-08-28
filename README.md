# AI Career Coach (Atelier)

One AI-native career platform: **Career Coach**, **Resume Studio**, and **Interview Coach** on a single persistent profile — as specified in the August 2026 PRD.

The product is the profile, memory, and resume/interview intelligence. Chat is only the interface.

## Stack (PRD §8)

| Layer | Implementation |
| --- | --- |
| Frontend | Next.js + TypeScript + Tailwind (`frontend/`) |
| Backend | FastAPI (`backend/`) |
| Orchestration | LangGraph supervisor + dedicated career / resume / interview workflows |
| AI | OpenAI `gpt-4o-mini` by default; optional Groq / Gemini / DeepSeek keys |
| Data | Postgres (Supabase pooler) in this project; SQLite still works for a fresh local `.env` |
| Knowledge / RAG | Markdown in `knowledge/` with embeddings when an API key is set |
| Files | Cloudflare R2 when configured; otherwise `backend/storage/` |
| Billing | Valid card checkout for Pro/Premium (Luhn + expiry + CVC). Stripe hosted checkout if Stripe keys are set |

## Run locally

**Backend** (Python 3.11+):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```

Set `LLM_API_KEY` in `backend/.env`. Without a key, coaching still runs in **demo mode**; skill-gap, roadmap, ATS, and interviews use catalog + heuristic fallbacks.

**Frontend**:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — the API lives at http://localhost:8000.

Seed admin (development only, created on first backend boot): `admin@careercoach.app` / `Admin1234!`.
Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` to choose your own. Outside `APP_ENV=development` no admin is
created unless `ADMIN_PASSWORD` is set, so a deployment never ships a known login.

If you are on Python 3.14, install with unpinned packages (`pip install -r requirements.txt`); older exact pins fail to build `pydantic-core`.

## Plans

- **Free** — limited resumes and mocks
- **Pro / Premium** — enter a valid card in Settings (name, number, expiry, CVC). Invalid cards are rejected. The full number and CVC are never stored
- **Downgrade to Free** — account password
- Test card that passes the checker: `4242 4242 4242 4242`, any future expiry, CVC `123`, any name

Password reset: `/forgot-password`. The API response is always the same generic message so it cannot be
used to discover which emails are registered. In development, with no SMTP configured, the reset link is
printed to the backend console. Outside development the link is never logged — configure SMTP or password
reset cannot complete.

Auth routes are rate limited (login 10/min, register and password reset per hour). Set
`RATE_LIMIT_ENABLED=false` if you need to load-test locally. Behind a reverse proxy, set
`TRUST_PROXY_HEADERS=true` so the limiter keys on the forwarded client address rather than putting every
user in the proxy's single bucket.

## Deploying

`SECRET_KEY` signs every session token. When `APP_ENV` is not a development value the app refuses to boot
if the key is missing, still the shipped default, or shorter than 32 characters — a forgeable key would let
anyone mint a token for any account. Generate one with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

`tests/test_core.py` covers agent and scoring logic in isolation; `tests/test_api.py` drives the HTTP API
end to end (auth, plan gating, ownership, quotas). The suite runs against a throwaway SQLite database in
a temp directory and ignores `backend/.env`, so it never touches your real data or calls a model provider.

## Coverage

- Auth, terms acceptance, forgot / reset password
- Career profile (PRD §6)
- Dashboard with readiness / resume health / interview performance (estimates, labeled)
- Career chat, skill-gap (Strong → Missing), 1/3/6/12 month roadmap with task controls
- Resume upload/parse, generate, edit, tailor, keyword/completeness scoring, versions, PDF/DOCX, cover letters
- Fact protection: missing information is flagged, not fabricated — on hand edits, generated drafts, resume
  prose, and cover letters. Facts come from your profile *and* from a resume you uploaded
- Adaptive mock interviews + STAR-style reports + history + Premium voice (re-checked on every voice call)
- Career memory (Pro) — the coach offers what it noticed and only stores it once you accept
- Usage limits by Free/Pro/Premium across resumes, interviews, chats, imports, skill-gap runs, and roadmaps
- LinkedIn paste + public GitHub analysis, insights, reminders, MCP tools
- Export (every table you own) + delete account behind a password confirmation
- Lightweight admin overview

The keyword/completeness score is deterministic, not model-generated, and does not predict whether a real
ATS or recruiter will pass a resume through. Readiness, resume health, and interview performance are
self-tracking estimates on the same footing.
