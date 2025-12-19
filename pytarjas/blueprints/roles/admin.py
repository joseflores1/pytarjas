# pytarjas/blueprints/roles/admin.py
"""
Admin blueprint for the dashboard.
Updated to include Form Versioning statistics.
"""

from flask import Blueprint, render_template, request, jsonify 
from pytarjas.models.user_models import User
from pytarjas.models.docs_models import Form # Added for version stats
from pytarjas.auth import login_required, admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/")
@login_required
@admin_required
def index():
    """
    Admin dashboard.
    
    Shows summary of users, form versions, and quick links.
    """
    # User statistics
    user_count = User.query.count()
    admin_count = User.query.filter_by(role="admin").count()
    worker_count = User.query.filter_by(role="worker").count()
    planner_count = User.query.filter_by(role="planner").count()
    client_count = User.query.filter_by(role="client").count()
    
    # Form versioning statistics
    # 'active_forms' represents the current templates available for work
    active_forms = Form.query.filter_by(is_active=True).count()
    # 'total_versions' includes all archived/historical versions
    total_versions = Form.query.count()
    
    if request.is_json:
        return jsonify({
            "success": True,
            "stats": {
                "total_users": user_count,
                "admin": admin_count,
                "worker": worker_count,
                "planner": planner_count,
                "client": client_count,
                "active_forms": active_forms,
                "total_form_versions": total_versions
            }
        }), 200
    
    return render_template(
        "admin/index.html",
        user_count=user_count,
        admin_count=admin_count,
        worker_count=worker_count,
        planner_count=planner_count,
        client_count=client_count,
        active_forms=active_forms,
        total_versions=total_versions
    )