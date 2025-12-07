from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import OrganizationForm
from app.models import Membership, Organization, Role

orgs_bp = Blueprint("orgs", __name__)


def _user_membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


@orgs_bp.route("/")
@login_required
def list_orgs():
    memberships = (
        Membership.query.filter_by(user_id=current_user.id, status="active")
        .order_by(Membership.created_at.desc())
        .all()
    )
    return render_template("orgs/list.html", memberships=memberships)


@orgs_bp.route("/orgs/create", methods=["GET", "POST"])
@login_required
def create_org():
    form = OrganizationForm()
    if form.validate_on_submit():
        slug_exists = Organization.query.filter_by(slug=form.slug.data.strip().lower()).first()
        if slug_exists:
            flash("Slug already taken. Choose another.", "warning")
            return render_template("orgs/create.html", form=form)
        org = Organization(
            name=form.name.data.strip(),
            slug=form.slug.data.strip().lower(),
            timezone=form.timezone.data.strip() or "UTC",
            default_workweek=form.default_workweek.data.strip() or "Mon-Fri",
            created_by_id=current_user.id,
        )
        db.session.add(org)
        db.session.flush()
        membership = Membership(user_id=current_user.id, org_id=org.id, role=Role.ADMIN, status="active", is_default=True)
        db.session.add(membership)
        db.session.commit()
        flash("Organization created and you are set as admin.", "success")
        return redirect(url_for("orgs.view_org", org_id=org.id))
    return render_template("orgs/create.html", form=form)


@orgs_bp.route("/orgs/<int:org_id>")
@login_required
def view_org(org_id):
    membership = _user_membership(org_id)
    if not membership:
        abort(403)
    org = membership.organization
    members = Membership.query.filter_by(org_id=org.id, status="active").all()
    return render_template("orgs/detail.html", org=org, membership=membership, members=members, Role=Role)


@orgs_bp.route("/orgs/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
def edit_org(org_id):
    membership = _user_membership(org_id)
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    org = membership.organization
    form = OrganizationForm(obj=org)
    if form.validate_on_submit():
        org.name = form.name.data.strip()
        org.slug = form.slug.data.strip().lower()
        org.timezone = form.timezone.data.strip() or "UTC"
        org.default_workweek = form.default_workweek.data.strip() or "Mon-Fri"
        db.session.commit()
        flash("Organization updated.", "success")
        return redirect(url_for("orgs.view_org", org_id=org.id))
    return render_template("orgs/edit.html", form=form, org=org)


@orgs_bp.route("/orgs/<int:org_id>/delete", methods=["POST"])
@login_required
def delete_org(org_id):
    membership = _user_membership(org_id)
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    org = membership.organization
    db.session.delete(org)
    db.session.commit()
    flash("Organization removed.", "info")
    return redirect(url_for("orgs.list_orgs"))


@orgs_bp.route("/orgs/<int:org_id>/set-default", methods=["POST"])
@login_required
def set_default_org(org_id):
    membership = _user_membership(org_id)
    if not membership:
        abort(403)
    Membership.query.filter_by(user_id=current_user.id).update({"is_default": False})
    membership.is_default = True
    db.session.commit()
    flash("Default organization updated.", "success")
    return redirect(request.referrer or url_for("orgs.list_orgs"))
