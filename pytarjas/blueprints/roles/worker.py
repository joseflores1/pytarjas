# pytarjas/worker.py
"""
Worker UI blueprint for field workers.
...
"""

from flask import (
    Blueprint, render_template, request, jsonify, g
)
from datetime import datetime, timezone
from pytarjas.auth import login_required
from pytarjas.models.docs_models import Task 

# Create blueprint with URL prefix /worker
bp = Blueprint("worker", __name__, url_prefix="/worker")


@bp.route("/") # NEW: The root /worker/ is now the index
@login_required
def index():
    """
    Worker dashboard - main landing page for workers.
    ...
    """
    # FIX: Initialize all variables to 0 to prevent UnboundLocalError 
    pending_count = 0
    in_progress_count = 0
    completed_today = 0
    total_assigned = 0

    # Query statistics based on user role
    if g.user.role == "worker":
        # Workers see only their assigned tasks
        pending_count = Task.query.filter_by(
            worker_id=g.user.id,
            status="pending"
        ).count()
        
        in_progress_count = Task.query.filter_by(
            worker_id=g.user.id,
            status="in_progress"
        ).count()
        
        # Completed today (since the start of the current UTC day)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        completed_today = Task.query.filter(
            Task.worker_id == g.user.id,
            Task.status == "completed",
            Task.completed_at >= today_start
        ).count()
        
        total_assigned = Task.query.filter_by(
            worker_id=g.user.id
        ).count()
    
    # Check if request wants JSON (from PWA/AJAX)
    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({
            "success": True,
            "user": {
                "id": g.user.id,
                "username": g.user.username,
                "role": g.user.role,
                "email": g.user.email
            },
            "dashboard": {
                "pending_tasks": pending_count,
                "in_progress_tasks": in_progress_count,
                "completed_today": completed_today,
                "total_assigned": total_assigned
            }
        }), 200
    
    # HTML request: render the dashboard template
    return render_template(
        "worker/index.html",
        user=g.user,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_today=completed_today,
        total_assigned=total_assigned
    )


@bp.route("/profile")
@login_required
def profile():
    return render_template(
        "worker/profile.html",
        user=g.user
    )


@bp.route("/help")
@login_required
def help_page():
    return render_template(
        "worker/help.html",
        user=g.user
    )