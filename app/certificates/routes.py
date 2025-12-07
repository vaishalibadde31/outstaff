from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import CertificateForm, CertificateTypeForm
from app.models import Certificate, CertificateStatus, CertificateType, Membership, Role

certificates_bp = Blueprint("certificates", __name__, url_prefix="/orgs/<int:org_id>/certificates")


def _membership(org_id):
    return Membership.query.filter_by(user_id=current_user.id, org_id=org_id, status="active").first()


def _require_membership(org_id):
    membership = _membership(org_id)
    if not membership:
        abort(403)
    return membership


@certificates_bp.route("/", methods=["GET", "POST"])
@login_required
def list_certificates(org_id):
    membership = _require_membership(org_id)
    types = CertificateType.query.filter_by(org_id=org_id).order_by(CertificateType.name.asc()).all()
    members = Membership.query.filter_by(org_id=org_id, status="active").all()
    certificates = (
        Certificate.query.filter_by(org_id=org_id)
        .order_by(Certificate.expiry_date.asc().nullslast(), Certificate.created_at.desc())
        .all()
    )

    certificate_form = CertificateForm()
    type_form = CertificateTypeForm()

    type_choices = [(t.id, t.name) for t in types]
    certificate_form.type_id.choices = type_choices
    user_choices = [(m.user.id, m.user.name) for m in members]
    certificate_form.user_id.choices = user_choices if membership.role == Role.ADMIN else [(current_user.id, current_user.name)]
    if membership.role != Role.ADMIN:
        certificate_form.status.choices = [(CertificateStatus.DRAFT.value, CertificateStatus.DRAFT.name.title())]

    if certificate_form.submit.data and certificate_form.validate_on_submit():
        cert = Certificate(
            user_id=certificate_form.user_id.data,
            org_id=org_id,
            type_id=certificate_form.type_id.data,
            issue_date=certificate_form.issue_date.data,
            expiry_date=certificate_form.expiry_date.data,
            attachment_url=certificate_form.attachment_url.data or None,
            status=CertificateStatus(certificate_form.status.data)
            if membership.role == Role.ADMIN
            else CertificateStatus.DRAFT,
            notes=certificate_form.notes.data or None,
            verified_by_id=current_user.id if membership.role == Role.ADMIN else None,
        )
        db.session.add(cert)
        db.session.commit()
        flash("Certificate saved.", "success")
        return redirect(url_for("certificates.list_certificates", org_id=org_id))

    if type_form.submit.data and type_form.validate_on_submit():
        if membership.role != Role.ADMIN:
            abort(403)
        cert_type = CertificateType(org_id=org_id, name=type_form.name.data.strip(), description=type_form.description.data)
        db.session.add(cert_type)
        db.session.commit()
        flash("Certificate type added.", "success")
        return redirect(url_for("certificates.list_certificates", org_id=org_id))

    expiring_soon = [
        c
        for c in certificates
        if c.expiry_date and c.expiry_date <= date.today() + timedelta(days=30) and c.status != CertificateStatus.EXPIRED
    ]
    return render_template(
        "certificates/list.html",
        org=membership.organization,
        membership=membership,
        certificates=certificates,
        certificate_form=certificate_form,
        type_form=type_form,
        expiring_soon=expiring_soon,
        CertificateStatus=CertificateStatus,
        Role=Role,
    )


@certificates_bp.route("/<int:certificate_id>/status", methods=["POST"])
@login_required
def update_status(org_id, certificate_id):
    membership = _require_membership(org_id)
    if membership.role != Role.ADMIN:
        abort(403)
    cert = Certificate.query.filter_by(id=certificate_id, org_id=org_id).first_or_404()
    new_status = request.form.get("status")
    if new_status not in [s.value for s in CertificateStatus]:
        abort(400)
    cert.status = CertificateStatus(new_status)
    cert.verified_by_id = current_user.id
    db.session.commit()
    flash("Certificate status updated.", "success")
    return redirect(request.referrer or url_for("certificates.list_certificates", org_id=org_id))


@certificates_bp.route("/<int:certificate_id>/delete", methods=["POST"])
@login_required
def delete_certificate(org_id, certificate_id):
    membership = _require_membership(org_id)
    cert = Certificate.query.filter_by(id=certificate_id, org_id=org_id).first_or_404()
    if membership.role != Role.ADMIN and cert.user_id != current_user.id:
        abort(403)
    db.session.delete(cert)
    db.session.commit()
    flash("Certificate removed.", "info")
    return redirect(request.referrer or url_for("certificates.list_certificates", org_id=org_id))
