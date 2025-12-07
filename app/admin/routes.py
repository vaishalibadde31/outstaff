from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import InviteForm
from app.models import Membership, Role, User

admin_bp = Blueprint("admin", __name__, url_prefix="/orgs/<int:org_id>/admin")


def _membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


def _require_admin(org_id):
    membership = _membership(org_id)
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    return membership


def _admin_count(org_id):
    return Membership.query.filter_by(org_id=org_id, role=Role.ADMIN, status="active").count()


@admin_bp.route("/members", methods=["GET", "POST"])
@login_required
def manage_members(org_id):
    membership = _require_admin(org_id)
    org = membership.organization
    invite_form = InviteForm()
    members = Membership.query.filter_by(org_id=org_id, status="active").all()

    if invite_form.validate_on_submit():
        email = invite_form.email.data.lower().strip()
        role = Role(invite_form.role.data)
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No existing account found for that email. Ask the user to register first.", "warning")
            return redirect(url_for("admin.manage_members", org_id=org_id))

        membership_record = Membership.query.filter_by(user_id=user.id, org_id=org_id).first()
        if membership_record:
            membership_record.status = "active"
            membership_record.role = role
        else:
            membership_record = Membership(user_id=user.id, org_id=org_id, role=role, status="active")
            db.session.add(membership_record)

        has_default = Membership.query.filter_by(user_id=user.id, is_default=True).count()
        if not has_default:
            membership_record.is_default = True
        db.session.commit()
        flash(f"Added {user.name} to {org.name} as {role.value}.", "success")
        return redirect(url_for("admin.manage_members", org_id=org_id))

    return render_template("admin/members.html", org=org, membership=membership, members=members, invite_form=invite_form)


@admin_bp.route("/members/<int:membership_id>/role", methods=["POST"])
@login_required
def update_role(org_id, membership_id):
    _require_admin(org_id)
    member = Membership.query.filter_by(id=membership_id, org_id=org_id).first_or_404()
    new_role = request.form.get("role")
    if new_role not in [Role.ADMIN.value, Role.MEMBER.value]:
        abort(400)
    if member.role == Role.ADMIN and new_role != Role.ADMIN.value and _admin_count(org_id) <= 1:
        flash("Cannot demote the last admin.", "warning")
        return redirect(request.referrer or url_for("admin.manage_members", org_id=org_id))
    member.role = Role(new_role)
    db.session.commit()
    flash("Role updated.", "success")
    return redirect(request.referrer or url_for("admin.manage_members", org_id=org_id))


@admin_bp.route("/members/<int:membership_id>/remove", methods=["POST"])
@login_required
def remove_member(org_id, membership_id):
    _require_admin(org_id)
    member = Membership.query.filter_by(id=membership_id, org_id=org_id).first_or_404()
    if member.role == Role.ADMIN and _admin_count(org_id) <= 1:
        flash("Cannot remove the last admin.", "danger")
        return redirect(request.referrer or url_for("admin.manage_members", org_id=org_id))
    member.status = "removed"
    db.session.commit()
    flash("Member removed from organization.", "info")
    return redirect(request.referrer or url_for("admin.manage_members", org_id=org_id))


@admin_bp.route("/invites/<int:invite_id>/revoke", methods=["POST"])
@login_required
def revoke_invite(org_id, invite_id):
    abort(404)


@admin_bp.route("/invites/accept/<token>", methods=["GET"])
def accept_invite(org_id, token):
    abort(404)
