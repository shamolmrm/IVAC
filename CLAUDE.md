# IVAC — Instructions for Claude

## Project
Visa application processing software for Indian visa applicants in Bangladesh (applicant portal, admin dashboard, document OCR, payment ledger, invoices). Not affiliated with IVAC. Plan: `docs/00-MASTER-PLAN.md`.

## Working rules
- The owner communicates in Bengali/Banglish; reply in Bengali.
- Work one task at a time. Plan → implement → test → update `docs/`. Do not start the next task automatically.
- Never commit secrets. Only `.env.example` goes in Git.
- Passport and personal data are sensitive: encrypt, restrict by role, audit-log every access.
- IVAC automation (login sessions, slot monitoring, booking, OTP) is NOT built until IVAC's official permission/API is confirmed. CAPTCHA is always solved by a human; never bypass rate limits or security controls.
- Never present the site as IVAC or as an official government service.

## Git & deploy
- Remotes: `origin` (github.com/shamolbro/IVAC) and `mirror` (github.com/shamolmrm/IVAC).
- After every completed change: commit, then `.\scripts\push-all.ps1` (both remotes).
- Deploy with `bash scripts/deploy.sh` (Git Bash). Live: https://ivac.supersoftltd.com
- Shared VPS: never touch other apps' containers or volumes.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
