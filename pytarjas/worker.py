# pytarjas/worker.py
"""
Worker UI blueprint for field workers.

This blueprint provides HTML pages and UI views for workers.
For API operations on tasks, use the /tasks/ blueprint instead.

Separation of concerns:
- worker.py = UI pages (HTML templates)
- tasks.py = API operations (JSON endpoints)

This keeps the code organized and allows other roles (planners)
to use the same tasks API with their own UI.
"""

from flask import (
    Blueprint, render_template, request, jsonify, g
)
from datetime import datetime, timezone
from pytarjas.auth import login_required
from pytarjas.models.docs_models import Document

# Create blueprint with URL prefix /worker
bp = Blueprint("worker", __name__, url_prefix="/worker")


@bp.route("/")
@bp.route("/index")
@login_required
def index():
    """
    Worker dashboard - main landing page for workers.
    
    Displays:
    - Summary statistics (pending, in progress, completed today)
    - Quick actions
    - Recent activity
    - Link to task list
    
    This view supports both HTML and JSON responses:
    - HTML: Renders the PWA template
    - JSON: Returns dashboard data for AJAX calls
    
    Access control:
    - Must be logged in
    - Any authenticated user can access (workers, planners, admins)
    - Data shown is role-based (workers see their tasks, others see all)
    
    Returns:
        HTML: Rendered worker dashboard template
        JSON: Dashboard statistics
    """
    # FIX: Initialize all variables to 0 to prevent UnboundLocalError 
    # for non-worker roles (Admin, Planner, Client).
    pending_count = 0
    in_progress_count = 0
    completed_today = 0
    total_assigned = 0

    # Query statistics based on user role
    if g.user.role == "worker":
        # Workers see only their assigned documents
        pending_count = Document.query.filter_by(
            worker_id=g.user.id,
            status="pending"
        ).count()
        
        in_progress_count = Document.query.filter_by(
            worker_id=g.user.id,
            status="in_progress"
        ).count()
        
        # Completed today (last 24 hours)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        completed_today = Document.query.filter(
            Document.worker_id == g.user.id,
            Document.status == "completed",
            Document.completed_at >= today_start
        ).count()
        
        total_assigned = Document.query.filter_by(
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
    """
    Worker profile page.
    
    Displays:
    - User information
    - Performance statistics
    - Recent activity history
    
    Access control:
    - Must be logged in
    
    Returns:
        HTML: Rendered profile template
    """
    # TODO: Implement profile page
    # For now, just show basic user info
    return render_template(
        "worker/profile.html",
        user=g.user
    )


@bp.route("/help")
@login_required
def help_page():
    """
    Help and documentation page for workers.
    
    Displays:
    - How to use the PWA
    - Offline mode instructions
    - FAQ
    - Contact information
    
    Access control:
    - Must be logged in
    
    Returns:
        HTML: Rendered help template
    """
    # TODO: Implement help page
    return render_template(
        "worker/help.html",
        user=g.user
    )