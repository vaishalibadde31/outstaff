from flask import Blueprint, render_template, redirect, url_for, abort, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Note, Membership, Organization
from app.forms import NoteForm

notes_bp = Blueprint(
    "notes",
    __name__,
    url_prefix="/orgs/<int:org_id>/notes"
)


def _user_membership(org_id):
    return Membership.query.filter_by(
        user_id=current_user.id,
        org_id=org_id,
        status="active"
    ).first()


# 🔹 LIST + CREATE NOTES
@notes_bp.route("/", methods=["GET", "POST"])
@login_required
def notes_page(org_id):

    membership = _user_membership(org_id)
    if not membership:
        abort(403)

    org = membership.organization
    form = NoteForm()

    if form.validate_on_submit():
        note = Note(
            org_id=org_id,
            author_id=current_user.id,
            content=form.content.data.strip()
        )

        db.session.add(note)
        db.session.commit()

        flash("Note added successfully.", "success")

        return redirect(url_for("notes.notes_page", org_id=org_id))

    notes = (
        Note.query
        .filter_by(org_id=org_id)
        .order_by(Note.created_at.desc())
        .all()
    )

    return render_template(
        "notes/list.html",
        org=org,
        notes=notes,
        form=form
    )


# 🔹 DELETE NOTE
@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(org_id, note_id):

    membership = _user_membership(org_id)
    if not membership:
        abort(403)

    note = Note.query.get_or_404(note_id)

    if note.author_id != current_user.id:
        abort(403)

    db.session.delete(note)
    db.session.commit()

    flash("Note deleted.", "info")

    return redirect(url_for("notes.notes_page", org_id=org_id))