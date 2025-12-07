# Time Tracking Module Specification (OutStaff)

## Purpose and Scope
- Deliver a feature-rich, multi-page time tracking module integrated into OutStaff’s organizations and roles.
- Target: accurate time capture, approvals, reporting, budgeting, compliance (overtime/holiday), and integrations readiness.
- Out of scope for v1 of this module: payroll calculations, billing/invoicing, geo-fencing; hooks should exist for later.

## Personas and Roles
- **Employee/Member**: logs time, edits drafts, submits for approval, views history and status.
- **Approver/Admin**: reviews/approves/returns entries, locks periods, manages projects/activities, adjusts policies.
- **Manager (future)**: portfolio reports, workload balancing across teams.
- **Auditor (future)**: read-only access to logs and approvals history.

## Key Objectives
- Make time capture fast (few clicks), error-resistant (overlap/duplicate checks), and transparent (status + comments).
- Support organizational policies: workweek defaults, overtime thresholds, holiday calendars, approval rules.
- Provide actionable reporting: summaries by user, project, client, date range, and exportable data.

## Information Architecture (Multi-Page)
- **Dashboard**: high-level summary (week hours, pending approvals, flagged entries).
- **My Time**: daily/weekly logging, calendar view, quick timers, bulk edit of drafts.
- **Approvals** (admin): queue of submitted entries, bulk approve/return with comments, filters by user/project/date.
- **Projects/Activities**: CRUD for projects/clients/activities; set billable/non-billable, budgets, hour caps.
- **Policies & Periods**: workweek defaults, overtime rules, lock dates/periods, holiday calendar import.
- **Reports**: presets (weekly, monthly) and custom filters; export CSV; saved views; charts (stacked by project/user).
- **Audit Trail**: log of approvals, edits, deletions, policy changes.

## Functional Requirements
### Time Entry Capture
- Entry fields: date, start/end or duration, project/activity, location (text), notes, billable flag, tags.
- Modes: manual entry, start/stop timer, clone previous entry, bulk add via multi-select dates.
- Validations: no overlap per user; end after start; required project if policy says so; duration caps; timezone-aware.
- Draft vs. submitted: employees can edit/delete drafts; submitted entries are immutable except by admin return.

### Approvals Workflow
- States: draft → submitted → approved | returned.
- Approver actions: approve, return with reason, bulk actions, reassign approver (future).
- Locks: approve/lock prevents further edits; admin can unlock with audit note.
- Last-admin guard: cannot leave org without an approver/admin.

### Projects/Activities
- Entities: Project (name, client, code, billable flag, status), Activity/Task (optional).
- Budgets: hours cap per project and/or per period; warnings at thresholds.
- Visibility: restrict project selection to assigned users (optional toggle).

### Policies & Calendars
- Workweek defaults per org; required minimum break (optional); max daily/weekly hours.
- Overtime rules: thresholds per day/week; classify hours segments (regular, OT1, OT2).
- Holiday calendar per org (import CSV/ICS); holiday hours tagged automatically; option to block logging on holidays.
- Period locks: close weeks/months; admin unlock with audit reason.

### Reporting & Exports
- Views: by user, by project, by client, by status, by date range; compare planned vs. actual (future).
- Metrics: total hours, billable vs. non-billable, overtime totals, approval latency.
- Exports: CSV per filter; include status, approvals, comments, project, billable flag, durations, tags.
- Saved reports: store filter sets per user; shareable links for admins.

### Audit and Compliance
- Audit log for create/edit/delete, status changes, approvals/returns, policy changes, lock/unlock actions.
- Surface reason/comments on returns and unlocks.
- Retention policy configurable per org.

### Notifications (In-App First)
- In-app banners/toasts for returns, approvals, nearing budgets.
- Optional email/webhook hooks (future) for submissions/approvals/threshold alerts.

## Data Model (Conceptual)
- **TimeEntry**: user_id, org_id, project_id, activity_id, date, start_at, end_at, duration_minutes, status, billable, tags, notes, approved_by, approved_at, return_reason, locked_at.
- **Project**: org_id, name, client, code, billable_flag, status, budget_hours, budget_period (weekly/monthly/total).
- **Activity**: org_id, project_id, name, code (optional), active flag.
- **Policy**: org_id, workweek, max_daily_hours, max_weekly_hours, overtime_daily_threshold, overtime_weekly_threshold, require_project, lock_after_days.
- **PeriodLock**: org_id, start_date, end_date, locked_by, locked_at, reason, unlocked_by, unlocked_at.
- **Holiday**: org_id, date, name, region (optional).
- **ApprovalLog**: time_entry_id, action (submit/approve/return/unlock), actor_id, timestamp, comment.
- **ReportPreset**: org_id, owner_id, name, filters (JSON), shared flag.

## UX Notes (Light Theme, Green Accent)
- Dashboard cards for hours, pending approvals, OT flags; trend sparkline.
- My Time: calendar + list hybrid; quick “start timer” button; smart defaults (last project/activity); empty states with CTA.
- Approvals: table with bulk checkboxes, inline comment on return, status chips; filter pills (user, project, date, status).
- Projects: budget progress bars (green → amber → red); billable badge.
- Policies: clear warnings when rules will block submission; lock indicators on dates.
- Reports: chart + table; sticky filter bar; export button prominent.
- Accessibility: keyboard navigation, clear focus states, descriptive labels.

## Security & Permissions
- Org-scoped access; employees can only see their entries; admins see all.
- Admin-only: approvals, locks, policy edits, project/activity CRUD, report sharing management.
- Server-side enforcement of status transitions and locks (no client trust).

## Delivery Phases (Module)
- **Phase A: Core Logging** — manual entries, validations, statuses, overlap checks, My Time + Dashboard summary.
- **Phase B: Approvals & Locks** — approval queue, return reasons, lock/unlock periods, audit logs.
- **Phase C: Projects/Activities & Budgets** — CRUD, assignment toggle, budget tracking, billable flag.
- **Phase D: Policies & Holidays** — workweek, overtime thresholds, holiday calendar, blocking rules.
- **Phase E: Reporting & Exports** — filters, CSV export, saved reports, charts.
- **Phase F: Timers & UX polish** — start/stop timers, bulk edit, smart defaults, accessibility pass.

## Success Criteria
- <1% overlap validation failures after submission (indicates preventive UX).
- Approval latency tracked; median <24h in org test data.
- Budget warnings fire at thresholds; locked periods prevent edits.
- Exports reconcile with on-screen totals; audit logs capture all status transitions and policy changes.
