# Master plan

Status: **Phase 0 done (2026-11-04)** — infrastructure (repo, subdomain, deploy pipeline, placeholder page).

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

## Open questions
1. Users: agency staff (B2B), applicants (B2C), or both?
2. Indian visa only, or other countries later?
3. Any official contact/permission with IVAC?
