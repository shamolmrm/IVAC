# IVAC Visa Assistant

Visa application processing software for Indian visa applicants in Bangladesh: applicant portal, document OCR, admin dashboard, payment ledger and invoices. Not affiliated with IVAC or any government body.

- **Live:** https://ivac.supersoftltd.com
- **Status:** Phase 1 — tasks 1–3 done: skeleton, accounts (register, login, email verification, password reset, lockout, audit log) and mobile OTP verification. Email and SMS sending switch on once SMTP and an SMS provider are configured. Plan: [docs/01-PHASE-1-PLAN.md](docs/01-PHASE-1-PLAN.md).
- **Stack:** Next.js 16 + TypeScript + Tailwind CSS (pnpm), Python 3.12 FastAPI + SQLAlchemy 2 + Alembic, PostgreSQL 16, Redis 7, Docker Compose, Nginx.

## Layout
```
frontend/                 Next.js app (App Router)
backend/                  FastAPI modular monolith (app/modules/<domain>)
infrastructure/production docker-compose, nginx site, backup, domain setup
scripts/                  deploy.sh, push-all.ps1
docs/                     plans and progress
```

## Local development
```bash
docker compose up -d                                  # Postgres :5433, Redis :6380
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
cd frontend && pnpm install && pnpm dev               # http://localhost:3000
```

## Deploy
```bash
bash scripts/deploy.sh      # Git Bash; runs backend tests in Docker, then deploys committed HEAD
```
```powershell
.\scripts\push-all.ps1      # push to both GitHub remotes
```
