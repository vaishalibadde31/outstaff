import enum
import uuid
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateStatus(enum.Enum):
    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    DRAFT = "draft"


class TimeEntryStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RETURNED = "returned"


def generate_token():
    return uuid.uuid4().hex


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    memberships = db.relationship("Membership", backref="user", lazy=True, cascade="all, delete-orphan")
    certificates = db.relationship(
        "Certificate", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Certificate.user_id"
    )
    time_entries = db.relationship(
        "TimeEntry", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="TimeEntry.user_id"
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_org_admin(self, org_id: int) -> bool:
        membership = Membership.query.filter_by(user_id=self.id, org_id=org_id, status="active").first()
        return membership.role == Role.ADMIN if membership else False


class Organization(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    timezone = db.Column(db.String(80), default="UTC")
    default_workweek = db.Column(db.String(80), default="Mon-Fri")
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    memberships = db.relationship("Membership", backref="organization", lazy=True, cascade="all, delete-orphan")
    invitations = db.relationship("Invitation", backref="organization", lazy=True, cascade="all, delete-orphan")
    certificate_types = db.relationship(
        "CertificateType", backref="organization", lazy=True, cascade="all, delete-orphan"
    )
    certificates = db.relationship("Certificate", backref="organization", lazy=True, cascade="all, delete-orphan")
    time_entries = db.relationship("TimeEntry", backref="organization", lazy=True, cascade="all, delete-orphan")
    projects = db.relationship("Project", backref="organization", lazy=True, cascade="all, delete-orphan")
    activities = db.relationship("Activity", backref="organization", lazy=True, cascade="all, delete-orphan")
    policies = db.relationship("Policy", backref="organization", lazy=True, cascade="all, delete-orphan")
    period_locks = db.relationship("PeriodLock", backref="organization", lazy=True, cascade="all, delete-orphan")
    holidays = db.relationship("Holiday", backref="organization", lazy=True, cascade="all, delete-orphan")
    report_presets = db.relationship("ReportPreset", backref="organization", lazy=True, cascade="all, delete-orphan")
    approval_logs = db.relationship("ApprovalLog", backref="organization", lazy=True, cascade="all, delete-orphan")


class Membership(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.MEMBER, nullable=False)
    status = db.Column(db.String(50), default="active", nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),)


class Invitation(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), default=Role.MEMBER, nullable=False)
    token = db.Column(db.String(64), default=generate_token, nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    status = db.Column(db.Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    invited_by = db.relationship("User", foreign_keys=[invited_by_id])

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class CertificateType(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    certificates = db.relationship("Certificate", backref="certificate_type", lazy=True, cascade="all, delete-orphan")


class Certificate(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey("certificate_type.id"), nullable=False)
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    attachment_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(CertificateStatus), default=CertificateStatus.DRAFT, nullable=False)
    verified_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    verified_by = db.relationship("User", foreign_keys=[verified_by_id])


class TimeEntry(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity.id"), nullable=True)
    date = db.Column(db.Date, nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(TimeEntryStatus), default=TimeEntryStatus.DRAFT, nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    return_reason = db.Column(db.Text, nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    billable = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    approved_by = db.relationship("User", foreign_keys=[approved_by_id])
    project = db.relationship("Project", backref="time_entries", foreign_keys=[project_id])
    activity = db.relationship("Activity", backref="time_entries", foreign_keys=[activity_id])

    def update_duration(self):
        delta = self.end_at - self.start_at
        self.duration_minutes = int(delta.total_seconds() // 60)


class Project(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    client = db.Column(db.String(120), nullable=True)
    code = db.Column(db.String(50), nullable=True)
    billable = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default="active")
    budget_hours = db.Column(db.Integer, nullable=True)
    budget_period = db.Column(db.String(50), nullable=True)  # weekly, monthly, total

    activities = db.relationship("Activity", backref="project", lazy=True, cascade="all, delete-orphan")


class Activity(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class Policy(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    workweek = db.Column(db.String(80), default="Mon-Fri")
    max_daily_hours = db.Column(db.Integer, nullable=True)
    max_weekly_hours = db.Column(db.Integer, nullable=True)
    overtime_daily_threshold = db.Column(db.Integer, nullable=True)
    overtime_weekly_threshold = db.Column(db.Integer, nullable=True)
    require_project = db.Column(db.Boolean, default=False)
    lock_after_days = db.Column(db.Integer, nullable=True)
    require_break_minutes = db.Column(db.Integer, nullable=True)


class PeriodLock(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    locked_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(255), nullable=True)
    unlocked_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    unlocked_at = db.Column(db.DateTime, nullable=True)

    locked_by = db.relationship("User", foreign_keys=[locked_by_id])
    unlocked_by = db.relationship("User", foreign_keys=[unlocked_by_id])


class Holiday(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    region = db.Column(db.String(80), nullable=True)


class ApprovalLog(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entry.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)  # submit, approve, return, unlock
    comment = db.Column(db.Text, nullable=True)

    actor = db.relationship("User", foreign_keys=[actor_id])
    time_entry = db.relationship("TimeEntry", backref="approval_logs", foreign_keys=[time_entry_id])


class ReportPreset(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    filters = db.Column(db.JSON, nullable=False)
    shared = db.Column(db.Boolean, default=False)

    owner = db.relationship("User", foreign_keys=[owner_id])


class AuditLog(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target_type = db.Column(db.String(120), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.JSON, nullable=True)

    actor = db.relationship("User", foreign_keys=[actor_id])


class Note(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    content = db.Column(db.Text, nullable=False)

    # Relationships
    organization = db.relationship("Organization", backref=db.backref("notes", lazy=True, cascade="all, delete-orphan"))
    author = db.relationship("User", foreign_keys=[author_id])