# pytarjas/blueprints/roles/worker.py
"""
Worker UI blueprint updated for Form Versioning.
Ensures workers download the specific form version assigned to their tasks.
"""
from flask import Blueprint, render_template, jsonify, g
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from pytarjas.auth import login_required
from pytarjas.models.docs_models import Task, Form
from pytarjas.helper import wants_json

bp = Blueprint("worker", __name__, url_prefix="/worker")

@bp.route("/")
@login_required
def index():
    """Worker dashboard with version-aware statistics."""
    pending_count = 0
    in_progress_count = 0
    completed_today = 0

    if g.user.role == "worker":
        pending_count = Task.query.filter_by(worker_id=g.user.id, status="pending").count()
        in_progress_count = Task.query.filter_by(worker_id=g.user.id, status="in_progress").count()
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = Task.query.filter(
            Task.worker_id == g.user.id,
            Task.status == "completed",
            Task.completed_at >= today_start
        ).count()

    if wants_json():
        return jsonify({
            "success": True,
            "stats": {
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed_today": completed_today
            }
        })

    return render_template(
        "worker/index.html",
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_today=completed_today
    )

@bp.route("/tasks")
@login_required
def list_tasks():
    """
    List tasks for the worker. 
    Uses joinedload to fetch the specific Form version and questions for offline sync.
    """
    tasks = Task.query.filter_by(worker_id=g.user.id)\
        .options(joinedload(Task.form).joinedload(Form.questions))\
        .order_at(Task.created_at.desc()).all()

    tasks_data = []
    for task in tasks:
        # We use .display_name to show "Form Name (v2)" in the UI
        tasks_data.append({
            "id": task.id,
            "status": task.status,
            "client": task.planning.client_name if task.planning else "Direct Task",
            "form_name": task.form.display_name, 
            "form_id": task.form_id, # This points to the specific version ID
            "questions_count": len(task.form.questions),
            "record_data": task.record_data
        })

    if wants_json():
        return jsonify({"success": True, "tasks": tasks_data})

    return render_template("worker/task_list.html", tasks=tasks_data)

@bp.route("/profile")
@login_required
def profile():
    return render_template("worker/profile.html", user=g.user)