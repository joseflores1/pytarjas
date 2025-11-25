# pytarjas/admin.py
"""
Admin blueprint for the dashboard.

User management logic (list, create, edit, delete) has been moved to the
'users' blueprint for agnostic access by Admin and Planner roles.
"""

from flask import Blueprint, render_template, request, jsonify 
from pytarjas.models.user_models import User # Used only for counting users
from pytarjas.auth import login_required, admin_required

# Create blueprint with URL prefix /admin
bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@admin_required
def index():
    """
    Admin dashboard.
    
    Shows summary of users and quick links.
    """
    user_count = User.query.count()
    admin_count = User.query.filter_by(role="admin").count()
    worker_count = User.query.filter_by(role="worker").count()
    planner_count = User.query.filter_by(role="planner").count()
    client_count = User.query.filter_by(role="client").count()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "stats": {
                "total": user_count,
                "admin": admin_count,
                "worker": worker_count,
                "planner": planner_count,
                "client": client_count
            }
        }), 200
    
    # NOTE: The template (admin/index.html) is responsible for linking to the
    # new resource endpoints (users.list_users, plannings.index, etc.)
    return render_template(
        "admin/index.html",
        user_count=user_count,
        admin_count=admin_count,
        worker_count=worker_count,
        planner_count=planner_count,
        client_count=client_count
    )

# Removed: list_users, get_user, create_user, edit_user, delete_user
# These endpoints are now implemented in the 'users' blueprint (pytarjas/users.py)