from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import (
    ActivityForm,
    ApprovalDecisionForm,
    HolidayForm,
    PeriodLockForm,
    PolicyForm,
    ProjectForm,
    ReportFilterForm,
    TimeEntryForm,
)
from app.models import (
    Activity,
    ApprovalLog,
    Holiday,
    Membership,
    PeriodLock,
    Policy,
    Project,
    Role,
    TimeEntry,
    TimeEntryStatus,
)

time_bp = Blueprint("time", __name__, url_prefix="/orgs/<int:org_id>/time")


def _membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


def _require_membership(org_id):
    membership = _membership(org_id)
    if not membership:
        abort(403)
    return membership


def _require_admin(org_id):
    membership = _require_membership(org_id)
    if membership.role != Role.ADMIN:
        abort(403)
    return membership


def _to_int(value):
    try:
        return int(value) if value not in (None, "", 0) else None
    except (TypeError, ValueError):
        return None


def _policy(org_id):
    policy = Policy.query.filter_by(org_id=org_id).first()
    if not policy:
        policy = Policy(org_id=org_id)
        db.session.add(policy)
        db.session.commit()
    return policy


def _is_locked(org_id, entry_date):
    lock = (
        PeriodLock.query.filter(
            PeriodLock.org_id == org_id,
            PeriodLock.start_date <= entry_date,
            PeriodLock.end_date >= entry_date,
        )
        .order_by(PeriodLock.end_date.desc())
        .first()
    )
    return lock is not None


def _overlaps(user_id, org_id, start_at, end_at, exclude_id=None):
    query = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.org_id == org_id,
        TimeEntry.start_at < end_at,
        TimeEntry.end_at > start_at,
    )
    if exclude_id:
        query = query.filter(TimeEntry.id != exclude_id)
    return query.first() is not None


def _assign_choices(form, org_id):
    projects = Project.query.filter_by(org_id=org_id).order_by(Project.name.asc()).all()
    activities = Activity.query.filter_by(org_id=org_id, is_active=True).order_by(Activity.name.asc()).all()
    form.project_id.choices = [(0, "No project")] + [(p.id, p.name) for p in projects]
    form.activity_id.choices = [(0, "No activity")] + [(a.id, a.name) for a in activities]


@time_bp.route("/")
@login_required
def dashboard(org_id):
    membership = _require_membership(org_id)
    recent_entries = (
        TimeEntry.query.filter_by(user_id=current_user.id, org_id=org_id)
        .order_by(TimeEntry.start_at.desc())
        .limit(5)
        .all()
    )
    pending_approvals = (
        TimeEntry.query.filter_by(org_id=org_id, status=TimeEntryStatus.SUBMITTED)
        .order_by(TimeEntry.start_at.desc())
        .limit(5)
        .all()
    )
    this_week_start = datetime.utcnow().date() - timedelta(days=datetime.utcnow().date().weekday())
    week_total = (
        db.session.query(db.func.sum(TimeEntry.duration_minutes))
        .filter(
            TimeEntry.org_id == org_id,
            TimeEntry.user_id == current_user.id,
            TimeEntry.date >= this_week_start,
        )
        .scalar()
        or 0
    )
    org_week_total = (
        db.session.query(db.func.sum(TimeEntry.duration_minutes))
        .filter(TimeEntry.org_id == org_id, TimeEntry.date >= this_week_start)
        .scalar()
        or 0
    )
    return render_template(
        "time/dashboard.html",
        org=membership.organization,
        membership=membership,
        recent_entries=recent_entries,
        pending_approvals=pending_approvals,
        week_total=week_total,
        org_week_total=org_week_total,
        Role=Role,
    )


@time_bp.route("/my", methods=["GET", "POST"])
@login_required
def my_time(org_id):
    membership = _require_membership(org_id)
    policy = _policy(org_id)
    form = TimeEntryForm()
    _assign_choices(form, org_id)
    if membership.role != Role.ADMIN:
        form.status.choices = [
            (TimeEntryStatus.DRAFT.value, "Draft"),
            (TimeEntryStatus.SUBMITTED.value, "Submitted"),
        ]
    entries = (
        TimeEntry.query.filter_by(user_id=current_user.id, org_id=org_id)
        .order_by(TimeEntry.start_at.desc())
        .all()
    )

    if form.validate_on_submit():
        start_at = datetime.combine(form.date.data, form.start_at.data.time())
        end_at = datetime.combine(form.date.data, form.end_at.data.time())
        if end_at <= start_at:
            flash("End time must be after start time.", "warning")
            return render_template("time/my.html", org=membership.organization, membership=membership, form=form, entries=entries)
        if policy.require_project and (form.project_id.data or 0) == 0:
            flash("Project is required by policy.", "warning")
            return render_template("time/my.html", org=membership.organization, membership=membership, form=form, entries=entries)
        if _overlaps(current_user.id, org_id, start_at, end_at):
            flash("Time entry overlaps with an existing entry.", "warning")
            return render_template("time/my.html", org=membership.organization, membership=membership, form=form, entries=entries)
        if _is_locked(org_id, form.date.data):
            flash("This period is locked. Contact an admin.", "danger")
            return render_template("time/my.html", org=membership.organization, membership=membership, form=form, entries=entries)

        project_id = form.project_id.data if form.project_id.data else None
        activity_id = form.activity_id.data if form.activity_id.data else None
        entry = TimeEntry(
            user_id=current_user.id,
            org_id=org_id,
            project_id=project_id,
            activity_id=activity_id,
            date=form.date.data,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=0,
            billable=form.billable.data,
            tags=form.tags.data or None,
            notes=form.notes.data or None,
            status=TimeEntryStatus(form.status.data) if membership.role == Role.ADMIN else TimeEntryStatus.DRAFT,
        )
        entry.update_duration()
        db.session.add(entry)
        db.session.commit()
        flash("Time entry saved.", "success")
        return redirect(url_for("time.my_time", org_id=org_id))

    return render_template(
        "time/my.html",
        org=membership.organization,
        membership=membership,
        form=form,
        entries=entries,
        TimeEntryStatus=TimeEntryStatus,
        Role=Role,
    )


@time_bp.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(org_id, entry_id):
    membership = _require_membership(org_id)
    entry = TimeEntry.query.filter_by(id=entry_id, org_id=org_id).first_or_404()
    if membership.role != Role.ADMIN and entry.user_id != current_user.id:
        abort(403)
    if _is_locked(org_id, entry.date):
        flash("Entry is in a locked period.", "warning")
        return redirect(url_for("time.my_time", org_id=org_id))
    form = TimeEntryForm(obj=entry)
    _assign_choices(form, org_id)
    if membership.role != Role.ADMIN:
        form.status.choices = [
            (TimeEntryStatus.DRAFT.value, "Draft"),
            (TimeEntryStatus.SUBMITTED.value, "Submitted"),
        ]
    if request.method == "GET":
        form.date.data = entry.date
        form.start_at.data = entry.start_at
        form.end_at.data = entry.end_at
        form.project_id.data = entry.project_id or 0
        form.activity_id.data = entry.activity_id or 0
    if form.validate_on_submit():
        start_at = datetime.combine(form.date.data, form.start_at.data.time())
        end_at = datetime.combine(form.date.data, form.end_at.data.time())
        if end_at <= start_at:
            flash("End time must be after start time.", "warning")
            return render_template("time/edit.html", form=form, org=membership.organization, entry=entry)
        if _overlaps(entry.user_id, org_id, start_at, end_at, exclude_id=entry.id):
            flash("Time entry overlaps with an existing entry.", "warning")
            return render_template("time/edit.html", form=form, org=membership.organization, entry=entry)
        entry.date = form.date.data
        entry.project_id = form.project_id.data if form.project_id.data else None
        entry.activity_id = form.activity_id.data if form.activity_id.data else None
        entry.start_at = start_at
        entry.end_at = end_at
        entry.billable = form.billable.data
        entry.tags = form.tags.data or None
        entry.notes = form.notes.data or None
        if membership.role == Role.ADMIN:
            entry.status = TimeEntryStatus(form.status.data)
        entry.update_duration()
        db.session.commit()
        flash("Time entry updated.", "success")
        return redirect(url_for("time.my_time", org_id=org_id))
    return render_template("time/edit.html", form=form, org=membership.organization, entry=entry)


@time_bp.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(org_id, entry_id):
    membership = _require_membership(org_id)
    entry = TimeEntry.query.filter_by(id=entry_id, org_id=org_id).first_or_404()
    if membership.role != Role.ADMIN and entry.user_id != current_user.id:
        abort(403)
    if _is_locked(org_id, entry.date):
        flash("Entry is in a locked period.", "warning")
        return redirect(request.referrer or url_for("time.my_time", org_id=org_id))
    db.session.delete(entry)
    db.session.commit()
    flash("Time entry removed.", "info")
    return redirect(request.referrer or url_for("time.my_time", org_id=org_id))


@time_bp.route("/approvals", methods=["GET", "POST"])
@login_required
def approvals(org_id):
    membership = _require_admin(org_id)
    entries = (
        TimeEntry.query.filter_by(org_id=org_id, status=TimeEntryStatus.SUBMITTED)
        .order_by(TimeEntry.start_at.desc())
        .all()
    )
    decision_form = ApprovalDecisionForm()
    return render_template("time/approvals.html", org=membership.organization, membership=membership, entries=entries, decision_form=decision_form)


@time_bp.route("/entries/<int:entry_id>/approve", methods=["POST"])
@login_required
def approve_entry(org_id, entry_id):
    membership = _require_admin(org_id)
    form = ApprovalDecisionForm()
    entry = TimeEntry.query.filter_by(id=entry_id, org_id=org_id).first_or_404()
    if form.validate_on_submit():
        if _is_locked(org_id, entry.date):
            flash("Entry is in a locked period.", "warning")
            return redirect(request.referrer or url_for("time.approvals", org_id=org_id))
        entry.status = TimeEntryStatus.APPROVED
        entry.approved_by_id = current_user.id
        entry.approved_at = datetime.utcnow()
        entry.return_reason = None
        log = ApprovalLog(org_id=org_id, time_entry_id=entry.id, actor_id=current_user.id, action="approve", comment=form.comment.data)
        db.session.add(log)
        db.session.commit()
        flash("Entry approved.", "success")
    return redirect(request.referrer or url_for("time.approvals", org_id=org_id))


@time_bp.route("/entries/<int:entry_id>/return", methods=["POST"])
@login_required
def return_entry(org_id, entry_id):
    membership = _require_admin(org_id)
    form = ApprovalDecisionForm()
    entry = TimeEntry.query.filter_by(id=entry_id, org_id=org_id).first_or_404()
    if form.validate_on_submit():
        entry.status = TimeEntryStatus.RETURNED
        entry.approved_by_id = current_user.id
        entry.return_reason = form.comment.data or "Returned without comment"
        log = ApprovalLog(org_id=org_id, time_entry_id=entry.id, actor_id=current_user.id, action="return", comment=form.comment.data)
        db.session.add(log)
        db.session.commit()
        flash("Entry returned with feedback.", "info")
    return redirect(request.referrer or url_for("time.approvals", org_id=org_id))


@time_bp.route("/projects", methods=["GET", "POST"])
@login_required
def projects(org_id):
    membership = _require_admin(org_id)
    project_form = ProjectForm()
    activity_form = ActivityForm()
    project_form.status.data = project_form.status.data or "active"
    project_form.budget_period.data = project_form.budget_period.data or ""
    projects = Project.query.filter_by(org_id=org_id).order_by(Project.created_at.desc()).all()
    activities = Activity.query.filter_by(org_id=org_id).order_by(Activity.created_at.desc()).all()

    if project_form.validate_on_submit() and project_form.submit.data:
        budget_hours = _to_int(project_form.budget_hours.data)
        project = Project(
            org_id=org_id,
            name=project_form.name.data.strip(),
            client=project_form.client.data.strip() or None,
            code=project_form.code.data.strip() or None,
            billable=project_form.billable.data,
            status=project_form.status.data,
            budget_hours=budget_hours,
            budget_period=project_form.budget_period.data or None,
        )
        db.session.add(project)
        db.session.commit()
        flash("Project saved.", "success")
        return redirect(url_for("time.projects", org_id=org_id))

    activity_form.project_id.choices = [(0, "No project")] + [(p.id, p.name) for p in projects]
    if activity_form.validate_on_submit() and activity_form.submit.data and "activity" in request.form:
        activity = Activity(
            org_id=org_id,
            project_id=activity_form.project_id.data or None if activity_form.project_id.data != 0 else None,
            name=activity_form.name.data.strip(),
            code=activity_form.code.data.strip() or None,
            is_active=activity_form.is_active.data,
        )
        db.session.add(activity)
        db.session.commit()
        flash("Activity saved.", "success")
        return redirect(url_for("time.projects", org_id=org_id))

    return render_template(
        "time/projects.html",
        org=membership.organization,
        membership=membership,
        projects=projects,
        activities=activities,
        project_form=project_form,
        activity_form=activity_form,
    )


@time_bp.route("/policies", methods=["GET", "POST"])
@login_required
def policies(org_id):
    membership = _require_admin(org_id)
    policy = _policy(org_id)
    policy_form = PolicyForm(obj=policy)
    lock_form = PeriodLockForm()
    holiday_form = HolidayForm()
    locks = PeriodLock.query.filter_by(org_id=org_id).order_by(PeriodLock.start_date.desc()).all()
    holidays = Holiday.query.filter_by(org_id=org_id).order_by(Holiday.date.desc()).all()

    if policy_form.validate_on_submit() and policy_form.submit.data:
        policy.workweek = policy_form.workweek.data.strip() or "Mon-Fri"
        policy.max_daily_hours = _to_int(policy_form.max_daily_hours.data)
        policy.max_weekly_hours = _to_int(policy_form.max_weekly_hours.data)
        policy.overtime_daily_threshold = _to_int(policy_form.overtime_daily_threshold.data)
        policy.overtime_weekly_threshold = _to_int(policy_form.overtime_weekly_threshold.data)
        policy.require_project = policy_form.require_project.data
        policy.lock_after_days = _to_int(policy_form.lock_after_days.data)
        policy.require_break_minutes = _to_int(policy_form.require_break_minutes.data)
        db.session.commit()
        flash("Policies updated.", "success")
        return redirect(url_for("time.policies", org_id=org_id))

    if lock_form.validate_on_submit() and lock_form.submit.data and "lock" in request.form:
        lock = PeriodLock(
            org_id=org_id,
            start_date=lock_form.start_date.data,
            end_date=lock_form.end_date.data,
            locked_by_id=current_user.id,
            reason=lock_form.reason.data or None,
        )
        db.session.add(lock)
        db.session.commit()
        flash("Period locked.", "success")
        return redirect(url_for("time.policies", org_id=org_id))

    if holiday_form.validate_on_submit() and holiday_form.submit.data and "holiday" in request.form:
        holiday = Holiday(org_id=org_id, date=holiday_form.date.data, name=holiday_form.name.data, region=holiday_form.region.data or None)
        db.session.add(holiday)
        db.session.commit()
        flash("Holiday added.", "success")
        return redirect(url_for("time.policies", org_id=org_id))

    return render_template(
        "time/policies.html",
        org=membership.organization,
        membership=membership,
        policy=policy,
        policy_form=policy_form,
        lock_form=lock_form,
        holiday_form=holiday_form,
        locks=locks,
        holidays=holidays,
    )


@time_bp.route("/reports", methods=["GET", "POST"])
@login_required
def reports(org_id):
    membership = _require_membership(org_id)
    form = ReportFilterForm()
    projects = Project.query.filter_by(org_id=org_id).order_by(Project.name.asc()).all()
    users = (
        Membership.query.filter_by(org_id=org_id, status="active")
        .join(Membership.user)
        .order_by(Membership.created_at.desc())
        .all()
    )
    form.project_id.choices = [(0, "Any project")] + [(p.id, p.name) for p in projects]
    form.user_id.choices = [(0, "Any user")] + [(m.user.id, m.user.name) for m in users]

    entries_query = TimeEntry.query.filter_by(org_id=org_id)
    if form.validate_on_submit():
        if form.start_date.data:
            entries_query = entries_query.filter(TimeEntry.date >= form.start_date.data)
        if form.end_date.data:
            entries_query = entries_query.filter(TimeEntry.date <= form.end_date.data)
        if form.project_id.data and form.project_id.data != 0:
            entries_query = entries_query.filter(TimeEntry.project_id == form.project_id.data)
        if form.user_id.data and form.user_id.data != 0:
            entries_query = entries_query.filter(TimeEntry.user_id == form.user_id.data)
        if form.status.data:
            entries_query = entries_query.filter(TimeEntry.status == TimeEntryStatus(form.status.data))
    else:
        # default to last 30 days
        entries_query = entries_query.filter(TimeEntry.date >= datetime.utcnow().date() - timedelta(days=30))

    entries = entries_query.order_by(TimeEntry.start_at.desc()).all()
    total_minutes = sum(e.duration_minutes for e in entries)
    billable_minutes = sum(e.duration_minutes for e in entries if e.billable)

    return render_template(
        "time/reports.html",
        org=membership.organization,
        membership=membership,
        form=form,
        entries=entries,
        total_minutes=total_minutes,
        billable_minutes=billable_minutes,
    )
