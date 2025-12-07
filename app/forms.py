from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    EmailField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app.models import CertificateStatus, Role, TimeEntryStatus


def role_choices():
    return [(Role.ADMIN.value, "Admin"), (Role.MEMBER.value, "Member")]


class SignupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class OrganizationForm(FlaskForm):
    name = StringField("Organization name", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=255)])
    timezone = StringField("Timezone", default="UTC", validators=[Optional(), Length(max=80)])
    default_workweek = StringField("Default workweek", default="Mon-Fri", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Save organization")


class InviteForm(FlaskForm):
    email = EmailField("User email", validators=[DataRequired(), Email(), Length(max=255)])
    role = SelectField("Role", choices=role_choices(), validators=[DataRequired()])
    submit = SubmitField("Send invite")


class CertificateTypeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save type")


class CertificateForm(FlaskForm):
    user_id = SelectField("Employee", coerce=int, validators=[DataRequired()])
    type_id = SelectField("Certificate type", coerce=int, validators=[DataRequired()])
    issue_date = DateField("Issue date", validators=[Optional()])
    expiry_date = DateField("Expiry date", validators=[Optional()])
    attachment_url = StringField("Attachment URL", validators=[Optional(), Length(max=255)])
    status = SelectField(
        "Status",
        choices=[(s.value, s.name.title()) for s in CertificateStatus],
        validators=[DataRequired()],
        default=CertificateStatus.DRAFT.value,
    )
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save certificate")


class TimeEntryForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    project_id = SelectField("Project", coerce=int, validators=[Optional()])
    activity_id = SelectField("Activity", coerce=int, validators=[Optional()])
    start_at = DateTimeLocalField("Start time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    end_at = DateTimeLocalField("End time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    billable = BooleanField("Billable")
    tags = StringField("Tags", validators=[Optional(), Length(max=255)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=1000)])
    status = SelectField(
        "Status",
        choices=[(s.value, s.name.title()) for s in TimeEntryStatus],
        default=TimeEntryStatus.DRAFT.value,
        validators=[DataRequired()],
    )
    submit = SubmitField("Save time entry")


class ApprovalDecisionForm(FlaskForm):
    comment = TextAreaField("Comment", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Submit")


class ProjectForm(FlaskForm):
    name = StringField("Project name", validators=[DataRequired(), Length(max=120)])
    client = StringField("Client", validators=[Optional(), Length(max=120)])
    code = StringField("Code", validators=[Optional(), Length(max=50)])
    billable = BooleanField("Billable")
    status = SelectField("Status", choices=[("active", "Active"), ("on_hold", "On Hold"), ("closed", "Closed")])
    budget_hours = StringField("Budget hours", validators=[Optional(), Length(max=10)])
    budget_period = SelectField(
        "Budget period",
        choices=[("", "None"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("total", "Total")],
        validators=[Optional()],
    )
    submit = SubmitField("Save project")


class ActivityForm(FlaskForm):
    project_id = SelectField("Project", coerce=int, validators=[Optional()])
    name = StringField("Activity name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Code", validators=[Optional(), Length(max=50)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save activity")


class PolicyForm(FlaskForm):
    workweek = StringField("Workweek", validators=[Optional(), Length(max=80)])
    max_daily_hours = StringField("Max daily hours", validators=[Optional(), Length(max=5)])
    max_weekly_hours = StringField("Max weekly hours", validators=[Optional(), Length(max=5)])
    overtime_daily_threshold = StringField("Overtime daily threshold", validators=[Optional(), Length(max=5)])
    overtime_weekly_threshold = StringField("Overtime weekly threshold", validators=[Optional(), Length(max=5)])
    require_project = BooleanField("Require project selection")
    lock_after_days = StringField("Lock after days", validators=[Optional(), Length(max=5)])
    require_break_minutes = StringField("Required break minutes", validators=[Optional(), Length(max=5)])
    submit = SubmitField("Save policies")


class PeriodLockForm(FlaskForm):
    start_date = DateField("Start date", validators=[DataRequired()])
    end_date = DateField("End date", validators=[DataRequired()])
    reason = StringField("Reason", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Lock period")


class HolidayForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    region = StringField("Region", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Add holiday")


class ReportFilterForm(FlaskForm):
    start_date = DateField("Start date", validators=[Optional()])
    end_date = DateField("End date", validators=[Optional()])
    project_id = SelectField("Project", coerce=int, validators=[Optional()])
    user_id = SelectField("User", coerce=int, validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("", "Any")] + [(s.value, s.name.title()) for s in TimeEntryStatus],
        validators=[Optional()],
    )
    submit = SubmitField("Run report")
