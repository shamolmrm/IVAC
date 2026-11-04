# Phase 1 plan — in-house system

Decisions (owner, 2026-11-04):
- **Users:** both — agencies with staff (B2B) and individual applicants (B2C).
- **Scope:** Indian visa only for now. Keep the visa type as data, not hard-coded, so other countries can be added later.
- **IVAC permission:** none. No IVAC automation. Phase 1 uses an *assisted-manual* flow: the system prepares verified data and a checklist; a human enters it on the IVAC site and records the result back.

## Roles
| Role | Can do |
|---|---|
| Super admin (us) | Everything, all organizations, system settings |
| Agency owner | Own agency: staff, applicants, payments, reports |
| Agency manager | Applicants and staff assignment in own agency |
| Agency agent | Only applicants assigned to them |
| Applicant | Own profile, documents, status, invoices |

Tenant isolation: every record carries `organization_id` (individual applicants belong to a built-in "Direct" organization). Every query is filtered by organization and role — one applicant's data can never leak to another.

## Modules (`backend/app/modules/`)
| Module | Contents |
|---|---|
| auth | Register, login, email + mobile OTP verification, sessions, password reset, 2FA for staff |
| organizations | Agencies, staff invites, roles |
| applicants | Profile, family/group applications, duplicate detection (passport no. + DOB) |
| documents | Upload, encrypted storage, versioning, required-document checklist |
| ocr | Passport MRZ read + check-digit validation; BGD PDF text extraction; field cross-check |
| applications | Status workflow + per-applicant timeline; ready-to-submit gate; IVAC result entry (date, receipt upload) |
| payments | Ledger: service fee / IVAC fee / refund kept separate; idempotency keys; manual entry first, bKash gateway later |
| invoices | PDF invoice + receipt, sequential numbers |
| notifications | Email + Telegram (SMS later) |
| reports | Daily/monthly, per staff, per agency, revenue |
| audit | Who did what, when — every read of passport data included |
| imports | Bulk CSV/Excel applicant import with validation report |

## Application status workflow
`draft → documents_pending → ocr_review → data_verified → ready → submitted_to_ivac → appointment_booked → completed` (+ `on_hold`, `cancelled`, `refunded`). Every transition is logged in the timeline.

## Security
- Files encrypted at rest (AES-256-GCM, key from server secret), never publicly served; short-lived signed download links.
- Passport number and other sensitive fields encrypted in the database.
- Rate limits on login/OTP, account lockout, staff 2FA.
- Nightly encrypted DB + file backup.
- Consent text at registration; data retention/deletion policy.

## Infrastructure
Shared VPS (4 vCPU / 7.8 GB, already hosting other apps). Phase 1 adds containers `ivac-web` (Next.js), `ivac-api` (FastAPI), `ivac-worker` (OCR/queue), `ivac-postgres`, `ivac-redis` — est. 1.5–2 GB RAM. A dedicated server is only needed once real load shows it.

## Task list (one at a time, each: build → test → deploy)
1. ✅ Monorepo skeleton: Next.js frontend, FastAPI backend, Postgres, Redis, Alembic, CI tests in deploy (2026-11-04)
2. ✅ Auth: register/login, email verification, password reset/change, sessions, account lockout, audit log (2026-11-04; email sending waits for SMTP settings)
3. ✅ Mobile OTP verification: BD number check, hashed 6-digit codes, 5-min expiry, 5 attempts, resend throttle, one account per number (2026-11-04; sending waits for an SMS provider adapter)
4. ✅ Organizations: agencies (pending → super admin approval), Owner/Manager/Agent roles, invite links, member management, built-in Direct org, tenant isolation (404 for non-members) + tests (2026-11-04)
5. ✅ Applicant profile: B2C (self + family) and agency applicants, passport/NID AES-256-GCM encrypted + blind index, duplicate passport blocked per scope, same name+DOB warning, cross-tenant duplicates only in the audit log, agent sees only assigned, assignment API, every view audited (2026-11-04)
6. Encrypted document upload + checklist
7. Passport MRZ OCR + validation
8. BGD PDF extraction + cross-check with passport
9. Application status workflow + timeline
10. Ready-to-submit gate + copy-ready data sheet for IVAC entry
11. IVAC result entry (appointment date, receipt upload)
12. Payment ledger (manual entry) + idempotency
13. PDF invoices and receipts
14. Email + Telegram notifications
15. Applicant portal UI (B2C)
16. Agency dashboard UI (B2B) + staff assignment
17. Super admin panel
18. Bulk CSV/Excel import
19. Reports
20. Audit log viewer, backups, monitoring/alerts
21. bKash payment gateway (needs merchant account)
22. Security review + load test before public launch

## Needed from the owner (not blocking task 1)
- SMS provider for OTP (e.g. a Bangladeshi bulk-SMS service) — before task 3
- bKash merchant/PGW account — before task 21
- Service fee pricing per agency/applicant — before task 12
- A real sample passport + BGD file (with consent) for OCR testing — before tasks 7–8

## Operations notes
- **DATA_ENCRYPTION_KEY** (in `/home/ubuntu/docker/websites/ivac/.env` on the VPS) encrypts passport and NID numbers. The nightly DB backup does NOT include it. Keep an offline copy (password manager); without it the encrypted fields cannot be recovered. Never change it without a re-encryption migration.
- Super admin: `docker exec -it ivac-api python -m app.cli create-superadmin EMAIL "Name"`.
