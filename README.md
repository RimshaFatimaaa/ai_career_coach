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

Seed admin (created on first backend boot): `admin@careercoach.local` / `Admin1234!`

If you are on Python 3.14, install with unpinned packages (`pip install -r requirements.txt`); older exact pins fail to build `pydantic-core`.

## Plans

- **Free** — limited resumes and mocks
- **Pro / Premium** — enter a valid card in Settings (name, number, expiry, CVC). Invalid cards are rejected. The full number and CVC are never stored
- **Downgrade to Free** — account password
- Test card that passes the checker: `4242 4242 4242 4242`, any future expiry, CVC `123`, any name

Password reset: `/forgot-password`. If SMTP is not set and `APP_ENV=development`, the API returns a reset link you can open locally.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

## Coverage

- Auth, terms acceptance, forgot / reset password
- Career profile (PRD §6)
- Dashboard with readiness / resume health / interview performance (estimates, labeled)
- Career chat, skill-gap (Strong → Missing), 1/3/6/12 month roadmap with task controls
- Resume upload/parse, generate, edit, tailor, ATS, versions, PDF/DOCX, cover letters
- Fact protection: missing information is flagged, not fabricated
- Adaptive mock interviews + STAR-style reports + history + Premium voice
- Career memory (Pro), usage limits by Free/Pro/Premium
- LinkedIn paste + public GitHub analysis, insights, reminders, MCP tools
- Export + delete account
- Lightweight admin overview
