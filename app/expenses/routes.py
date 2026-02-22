from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Expense, Organization, Membership

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/orgs/<slug>/expenses", methods=["GET", "POST"])
@login_required
def index(slug):
    org = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check membership
    membership = Membership.query.filter_by(user_id=current_user.id, org_id=org.id, status="active").first()
    if not membership:
            flash("You must be a member of this organization to view expenses.", "error")
            return redirect(url_for("orgs.dashboard", slug=slug))

    if request.method == "POST":
        description = request.form.get("description")
        category = request.form.get("category")
        amount = request.form.get("amount")
        date_str = request.form.get("date")

        if not all([description, category, amount, date_str]):
            flash("All fields are required.", "error")
        else:
            try:
                amount_float = float(amount)
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                expense = Expense(
                    description=description,
                    category=category,
                    amount=amount_float,
                    date=date_obj,
                    user_id=current_user.id,
                    org_id=org.id
                )
                db.session.add(expense)
                db.session.commit()
                flash("Expense added successfully.", "success")
                return redirect(url_for("expenses.index", slug=slug))
            except ValueError:
                flash("Invalid amount or date format.", "error")

    expenses = Expense.query.filter_by(org_id=org.id).order_by(Expense.date.desc()).all()
    total_expenses = sum(e.amount for e in expenses)
    
    return render_template("expenses/index.html", org=org, expenses=expenses, total_expenses=total_expenses)