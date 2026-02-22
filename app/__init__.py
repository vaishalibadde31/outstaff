from pathlib import Path

from flask import Flask

from app.config import BaseConfig
from app.extensions import csrf, db, init_extensions, login_manager

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    app.config.from_object(BaseConfig)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_extensions(app)

    from app import models  # noqa: F401
    from app.auth.routes import auth_bp
    from app.orgs.routes import orgs_bp
    from app.admin.routes import admin_bp
    from app.certificates.routes import certificates_bp
    from app.time_entries.routes import time_bp
    from app.notes.routes import notes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(orgs_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(certificates_bp)
    app.register_blueprint(time_bp)
    app.register_blueprint(notes_bp)

    register_cli(app)
    register_context_processors(app)

    with app.app_context():
        db.create_all()

    return app


def register_cli(app: Flask):
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize database tables."""
        db.create_all()
        print("Database initialized.")


def register_context_processors(app: Flask):
    from app.models import Membership, Organization
    from flask_login import current_user

    @app.context_processor
    def inject_orgs():
        orgs = []
        active_membership = None
        if current_user.is_authenticated:
            orgs = list(
                Organization.query.join(Membership).filter(
                    Membership.user_id == current_user.id, Membership.status == "active"
                )
            )
            active_membership = (
                Membership.query.filter_by(user_id=current_user.id, is_default=True)
                .order_by(Membership.created_at.desc())
                .first()
            )
            if not active_membership and orgs:
                active_membership = (
                    Membership.query.filter_by(user_id=current_user.id, org_id=orgs[0].id)
                    .order_by(Membership.created_at.desc())
                    .first()
                )
        return dict(user_orgs=orgs, active_membership=active_membership)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User

        return User.query.get(int(user_id))
