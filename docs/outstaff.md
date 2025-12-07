# OutStaff Implementation Plan

## Purpose and Scope
- Build **OutStaff**, a Flask + Tailwind business management web application for organizations to manage users, roles, certificates, and employee time.
- Scope covers web UI, backend APIs, persistence, and operational readiness for an initial production launch (MVP with guardrails).
- Out of scope: native mobile apps, payroll calculations, SSO/SAML in v1 (design hooks included), and third-party HRIS integrations.

## Product Goals
- Simple onboarding: self-serve signup/login with email verification and password reset.
- Multi-organization: users can create, join, and switch between multiple organizations; org ownership is not exclusive.
- Role-driven access: enforce least-privilege via roles and per-organization permissions.
- Workforce admin: invite existing users, manage membership, permissions, and removals.
- Compliance support: track employee certificates with expiry visibility.
- Operational insight: time tracking for employees with exportable reporting.

## Target Users and Roles
- **Platform User**: any registered user (can belong to many organizations).
- **Org Admin**: per-organization admin; manages members, roles, invites, org settings, and sensitive data.
- **Org Member/Employee**: standard role for day-to-day tasks (certificates, timesheets).
- Future: custom roles with granular permissions (v2), auditor/read-only viewer.

## Technology Approach
- **Backend**: Flask (RESTful services), JWT sessions or secure server-side sessions, background jobs (Celery or RQ) if needed for emails.
- **Frontend**: Tailwind for styling; HTMX/Alpine or light JS for interactivity; form-first UX.
- **Data**: Relational DB (PostgreSQL preferred); migrations via Alembic.
- **Infrastructure**: Container-friendly (Dockerfile + Compose), environment-based config, email provider integration for invites and verification.
- **Security**: hashed passwords (bcrypt/argon2), CSRF protection, rate limiting on auth endpoints, audit trails for admin actions.

## Functional Modules

### 1) Authentication and Account Management
- Signup with email verification; login with session + refresh; logout everywhere.
- Password reset flow (email token); password change while authenticated.
- Session management: short-lived access token + refresh, revoke refresh on password change.
- Basic profile: name, avatar URL placeholder, notification preferences.
- Account deletion (soft delete; keep audit linkage).

### 2) Organizations
- Create/edit/delete organizations; ownership is per-user per-organization.
- Org settings: name, slug/code, logo, timezone, default workweek.
- Membership list with role assignment; invite acceptance ties membership to existing account.
- Switcher UI for users in multiple orgs; last-used org remembered.
- Soft-delete orgs; prevent deletion if outstanding compliance blockers (e.g., active certificates? configurable).

### 3) Roles and Permissions
- Built-in roles per organization: `Admin`, `Member/Employee`.
- Permission model: policy checks on every protected action; admin-only gates for sensitive endpoints (invites, role changes, org deletion).
- Admin controls: promote/demote members, revoke membership, view audit logs of role changes.
- Guardrails: block removal of last admin; audit every permission change.

### 4) User Invitations and Membership Management (Admin)
- Invite existing users by email to an organization; if account exists, they get an org invite; if not, they must sign up to accept.
- Invitation lifecycle: pending → accepted/expired/revoked; configurable expiry (e.g., 7 days).
- Admin actions: resend invite, revoke invite, assign role on invite, update role after acceptance, remove member (soft remove; keep historical time/cert data).
- Notifications: email for invite, acceptance confirmation to admin, optional in-app alerts.

### 5) Employee Certificate Management
- Certificate types: configurable per org (e.g., OSHA, CPR); fields: name, issuing authority, issue date, expiry date, document attachment URL/storage key, status (valid/expiring/expired).
- Employee certificate records linked to user + organization; multiple certificates per user.
- Views: list by employee, filter by status/expiry window; detail view per certificate.
- Workflows: upload/attach proof, mark as verified (admin), auto status updates based on expiry date.
- Alerts: upcoming expiry notifications to employee and admins (e.g., 30/7/1 days), dashboard badges.
- Audit: who added/verified/edited; history of changes.

### 6) Time Tracking
- Time entries: user, organization, project/task (optional), start/end timestamps or duration, notes, status (draft/submitted/approved).
- CRUD: employees create/edit/delete their own drafts; admins can approve/return entries; lock approved entries.
- Views: daily/weekly summaries, per-user and per-org rollups; filters by date range and member.
- Exports: CSV download per org and date range; include totals and entry-level detail.
- Compliance: prevent overlapping entries; timezone-aware; audit approvals/rejections with reason.

## Cross-Cutting Concerns
- **Authorization middleware**: consistent org + role checks on every request; organization context required on protected routes.
- **Audit logging**: record admin and sensitive actions (invites, role changes, org edits, certificate verification, time approvals).
- **Notifications**: email service abstraction; later in-app notifications; template library for invites, resets, expirations.
- **File handling**: storage abstraction for certificate documents (local/dev vs. S3-compatible in prod); virus scan hook optional.
- **Validation and UX**: inline form validation, meaningful errors, empty states, loading states; accessible components (Tailwind + semantic HTML).
- **Internationalization-ready**: text organized for future i18n; timezones per org.

## Data Model Outline (conceptual)
- User (id, email, password_hash, profile)
- Organization (id, name, slug, settings, timezone)
- Membership (user_id, org_id, role, status)
- Invitation (org_id, email, role, expires_at, status, token)
- CertificateType (org_id, name, description)
- Certificate (user_id, org_id, type_id, issue_date, expiry_date, attachment, status, verified_by)
- TimeEntry (user_id, org_id, project/task, start_at, end_at, duration, status, approved_by, notes)
- AuditLog (actor_id, org_id, action, target_type, target_id, metadata)

## UX and Navigation
- Landing/login/signup screens with clear CTA.
- Org switcher in nav; context-aware breadcrumbs.
- Admin console per org with tabs: Members, Invitations, Roles/Permissions, Settings, Audit.
- Employee views: My Certificates, My Time, Submit Time.
- Dashboards: at-a-glance cards for expiring certificates, pending invites, time approval queue.

## Security and Compliance
- Strong password policy; rate limit auth endpoints.
- CSRF on form submissions; session cookie security flags; HTTPS-only expectation.
- RBAC enforcement server-side; never trust client role data.
- Email verification required before org admin actions.
- Logging and monitoring hooks; privacy notice and data retention policy placeholders.

## Delivery Plan (phased)
- **Phase 1: Foundations** — Project scaffolding (Flask, Tailwind build), auth (signup/login/reset), email service, base layouts, DB migrations, seed roles.
- **Phase 2: Organizations & Roles** — Org CRUD, membership model, org switcher, role enforcement middleware, admin console skeleton.
- **Phase 3: Invitations & Membership Management** — Invite flows, acceptance UI, resend/revoke, role changes, membership removal, audit logging for admin actions.
- **Phase 4: Certificates** — Certificate types, certificate CRUD, file attachment handling, verification, expiry status calculations, notifications for expirations.
- **Phase 5: Time Tracking** — Time entry CRUD, validation (overlap, timezone), approvals, CSV export, dashboards.
- **Phase 6: Polishing & Readiness** — Accessibility, empty/loading states, performance checks, logging/metrics, deploy configs (Docker/Compose), smoke tests, error pages.

## Success Metrics (MVP)
- Auth flows: <2% failure on login/signup attempts; password reset success path validated.
- Invitations: acceptance rate tracked; latency from invite to usable account <2 minutes.
- Admin correctness: zero unauthorized role or org mutations in audit logs; last-admin protection works.
- Certificates: expiry alerts fire on schedule; status accuracy validated against sample data.
- Time tracking: no overlapping approved entries; CSV export matches UI totals.

