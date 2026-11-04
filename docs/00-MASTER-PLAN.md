# Master plan

Status: **Phase 1 in progress.** Phase 0 (infrastructure) done 2026-11-04; Phase 1 tasks 1–4 (skeleton, auth, mobile OTP, agencies + roles) done 2026-11-04.

## Phase 1 — in-house system (no IVAC dependency)
- Applicant portal: registration, mobile/email verification, document upload
- OCR: passport MRZ + BGD application file extraction, cross-check
- Admin dashboard: applicants, documents, staff roles, assignment, per-applicant timeline, reports
- Payment ledger: service fee / IVAC fee / refunds kept separate, reconciliation, idempotency, PDF invoices
- Bulk CSV/Excel import, Telegram/email notifications
- Security: encryption at rest, role-based access, audit log, duplicate protection, backups, safe retries

## Phase 2 — IVAC integration (blocked)
Only after confirming: IVAC official automation permission/API, session validity, and the permitted payment channel.
Form auto-fill and slot monitoring stay within permitted limits; OTP needs review; CAPTCHA is solved by a human.

## Decisions (2026-11-04)
1. Users: both — agencies with staff (B2B) and individual applicants (B2C).
2. Indian visa only for now.
3. No IVAC permission → Phase 1 uses an assisted-manual flow.

Details and task list: [01-PHASE-1-PLAN.md](01-PHASE-1-PLAN.md).
