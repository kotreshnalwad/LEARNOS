# LearnOS AI — Master Anything. AI Builds The Path.

> An AI-powered learning operating system that automatically discovers the best resources on the internet and builds your personalized, adaptive curriculum.

---

## Architecture

```
learnos/
├── backend/               # FastAPI + Python
│   ├── app/
│   │   ├── agents/        # AI pipeline agents
│   │   │   ├── search_agent.py        # Web/YouTube/GitHub search
│   │   │   ├── ranking_agent.py       # Quality scoring & dedup
│   │   │   ├── curriculum_agent.py    # Claude-powered roadmap gen
│   │   │   ├── tutor_agent.py         # Streaming AI tutor
│   │   │   ├── mastery_agent.py       # Comprehension evaluation
│   │   │   └── recommendation_agent.py # Resource freshness updates
│   │   ├── api/routes/    # FastAPI endpoints
│   │   ├── core/          # Config, auth, cache
│   │   ├── db/            # SQLAlchemy async engine
│   │   ├── models/        # ORM models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   └── migrations/        # Alembic migrations
│
└── frontend/              # Next.js 14 + TypeScript
    └── src/
        ├── app/           # App router pages
        ├── components/    # UI components
        ├── hooks/         # React Query hooks
        ├── lib/           # API client + SSE
        ├── stores/        # Zustand state
        └── types/         # TypeScript types
```

## AI Pipeline

```
User types topic
       ↓
  Search Agent          — Tavily, YouTube API, GitHub, arXiv
       ↓
  Ranking Agent         — authority × popularity × freshness × completeness
       ↓
  Curriculum Agent      — Claude generates modules → lessons → quizzes → projects
       ↓
  Roadmap saved         — PostgreSQL, SSE progress stream to client
       ↓
  Tutor Agent           — Claude streams real-time answers in lesson view
       ↓
  Mastery Agent         — Quiz scores + time + project → unlock next module
       ↓
  Recommendation Agent  — Background job refreshes stale resources (cron)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, TailwindCSS, Framer Motion |
| State | Zustand + React Query |
| Auth | Clerk |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL (Supabase) |
| Cache | Redis (Upstash) |
| Vector DB | Pinecone |
| AI | Claude (Anthropic), GPT-4 (OpenAI) |
| Search | Tavily, YouTube Data API, GitHub API, Semantic Scholar |
| Deploy | Vercel (frontend) + Railway (backend) |
| Monitoring | Sentry + PostHog |

---

## Quick Start

### Prerequisites
- Python 3.12+, Node.js 20+, Docker (optional)
- API keys: Clerk, Anthropic, Tavily, YouTube, OpenAI

### 1. Clone & configure

```bash
git clone https://github.com/yourorg/learnos.git
cd learnos

# Backend
cp backend/.env.example backend/.env
# Fill in backend/.env with your API keys

# Frontend
cp frontend/.env.example frontend/.env.local
# Fill in frontend/.env.local with your keys
```

### 2. Run with Docker (recommended)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Run locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/roadmaps/generate` | Stream roadmap generation (SSE) |
| `GET` | `/api/roadmaps` | List user roadmaps |
| `GET` | `/api/roadmaps/{id}` | Get roadmap with progress |
| `POST` | `/api/progress` | Update lesson progress |
| `GET` | `/api/quizzes/{id}` | Get quiz questions |
| `POST` | `/api/quizzes/submit` | Submit quiz answers |
| `POST` | `/api/tutor/chat` | Stream AI tutor response (SSE) |
| `GET` | `/api/users/me` | Get current user |
| `GET` | `/api/topics/trending` | Get trending topics |
| `GET` | `/api/recommendations/lesson/{id}` | Fresh resource suggestions |

---

## Deployment

### Frontend → Vercel

```bash
cd frontend
vercel --prod
```

Set environment variables in Vercel dashboard (copy from `.env.example`).

### Backend → Railway

```bash
# Install Railway CLI
npm i -g @railway/cli
railway login

cd backend
railway up
```

Set environment variables in Railway dashboard.

### Database → Supabase

1. Create project at [supabase.com](https://supabase.com)
2. Copy the connection string (URI) to `DATABASE_URL`
3. Run migrations: `alembic upgrade head`

---

## Development

```bash
# Backend tests
cd backend && pytest

# Frontend type check
cd frontend && npm run type-check

# Frontend lint
cd frontend && npm run lint
```

---

## Roadmap

**Phase 1 (MVP) ✅**
- Authentication, topic search, roadmap generation
- Lesson pages with resources, quiz, project
- AI Tutor (streaming), progress tracking, mastery gating

**Phase 2**
- Adaptive learning (adjust difficulty based on quiz scores)
- Voice tutor (Whisper + TTS)
- Project code reviews (AI evaluation)
- Skill assessments

**Phase 3**
- AI Mentor (long-form mentorship sessions)
- Live collaboration (study rooms)
- Team learning (enterprise)
- Learning analytics dashboard

---

## License

MIT © LearnOS AI
