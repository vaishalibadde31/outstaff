from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import LeaveRequest, Organization, Membership, Role
from app.utils import log_activity

leaves_bp = Blueprint("leaves", __name__)

@leaves_bp.route("/orgs/<slug>/leaves", methods=["GET", "POST"])
@login_required
def index(slug):
    org = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check membership
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
    if not membership:
        flash("You must be a member of this organization to view leave requests.", "error")
        return redirect(url_for("orgs.dashboard", slug=slug))

    if request.method == "POST":
        leave_type = request.form.get("type")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        reason = request.form.get("reason")

        if not all([leave_type, start_date_str, end_date_str]):
             flash("Type, Start Date, and End Date are required.", "error")
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                if end_date < start_date:
                    flash("End date cannot be before start date.", "error")
                else:
                    leave = LeaveRequest(
                        type=leave_type,
                        start_date=start_date,
                        end_date=end_date,
                        reason=reason,
                        user_id=current_user.id,
                        org_id=org.id
                    )
                    db.session.add(leave)
                    db.session.commit()
                    log_activity(org.id, current_user.id, f"Submitted a leave request for {leave_type}")
                    flash("Leave request submitted successfully.", "success")
                    return redirect(url_for("leaves.index", slug=slug))
            except ValueError:
                flash("Invalid date format.", "error")

    # Filter leaves based on role
    if membership.role == Role.ADMIN:
        leaves = LeaveRequest.query.filter_by(org_id=org.id).order_by(LeaveRequest.created_at.desc()).all()
    else:
        leaves = LeaveRequest.query.filter_by(org_id=org.id, user_id=current_user.id).order_by(LeaveRequest.created_at.desc()).all()

    return render_template("leaves/index.html", org=org, leaves=leaves, membership=membership, Role=Role)

@leaves_bp.route("/leaves/<int:id>/update_status", methods=["POST"])
@login_required
def update_status(id):
    leave = LeaveRequest.query.get_or_404(id)
    org = Organization.query.get(leave.org_id)
    
    # Check if current user is admin of this org
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
    if not membership or membership.role != Role.ADMIN:
        abort(403)
    
    new_status = request.form.get("status")
    if new_status in ["Approved", "Rejected"]:
        leave.status = new_status
        db.session.commit()
        log_activity(org.id, current_user.id, f"{new_status} leave request for {leave.user.name}")
        flash(f"Leave request {new_status.lower()}.", "success")
    else:
        flash("Invalid status.", "error")
        
    return redirect(url_for("leaves.index", slug=org.slug))