from app.extensions import db
from app.models import ActivityLog

def log_activity(org_id, user_id, action):
    """
    Logs an activity for an organization.
    """
    try:
        activity = ActivityLog(org_id=org_id, user_id=user_id, action=action)
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        # In a real app, we might log this error to a file or monitoring service
        # For now, we print it or pass to avoid breaking the main flow
        print(f"Failed to log activity: {e}")
        db.session.rollback()