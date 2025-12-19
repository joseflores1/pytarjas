# pytarjas/blueprints/artifacts/plannings.py
"""
Plannings API blueprint for managing work plannings and tasks.
Updated to support per-task worker assignment and dynamic records.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g, abort 
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid

from pytarjas.models.user_models import db, User
from pytarjas.models.docs_models import Planning, Task, Form   
from pytarjas.auth import login_required, planning_access_required
from pytarjas.helper import wants_json

bp = Blueprint("plannings", __name__, url_prefix="/plannings")

def check_planning_access(planning_id: str) -> Planning:
    """
    Check if current user has access to a planning and return it.
    """
    planning = Planning.query.options(
        joinedload(Planning.planner),
        joinedload(Planning.form),
        joinedload(Planning.tasks)
    ).get_or_404(planning_id)
    
    if g.user.role == "admin":
        return planning
    
    if g.user.role == "planner" and g.user.id == planning.planner_id:
        return planning
    
    abort(403)

@bp.route("/", methods=["GET"])
@login_required
@planning_access_required
def list_plannings():
    """
    List all plannings showing versioned form names.
    """
    status_filter = request.args.get('status', 'all')
    client_search = request.args.get('client_name', '').strip()
    
    query = Planning.query.options(
        joinedload(Planning.planner),
        joinedload(Planning.form)
    )
    
    if status_filter != 'all':
        query = query.filter(Planning.status == status_filter)
    
    if client_search:
        query = query.filter(Planning.client_name.ilike(f'%{client_search}%'))

    plannings = query.order_by(Planning.created_at.desc()).all()
    
    plannings_data = []
    for plan in plannings:
        plannings_data.append({
            "id": plan.id,
            "client_name": plan.client_name,
            "form_name": plan.form.display_name if plan.form else "N/A",
            "status": plan.status,
            "total_tasks": plan.total_tasks,
            "planner": plan.planner.username if plan.planner else "System",
            "created_at": plan.created_at.strftime('%d/%m/%Y %H:%M')
        })
    
    if wants_json():
        return jsonify({
            "success": True,
            "plannings": plannings_data
        })
    
    return render_template(
        "plannings/list_plannings.html",
        plannings=plannings_data,
        status_filter=status_filter,
        client_search=client_search
    )

@bp.route("/create", methods=["GET", "POST"])
@login_required
@planning_access_required
def create_planning():
    """
    Create a new planning using the latest active form version and assign tasks to workers.
    """
    if request.method == "GET":
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        
        # Fetch assignable users (workers and planners) for per-task assignment
        assignable_users = User.query.filter(
            User.role.in_(["worker", "planner"])
        ).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [{"id": f.id, "name": f.display_name} for f in active_forms],
                "assignable_users": [{"id": u.id, "username": u.username} for u in assignable_users]
            })
        
        return render_template(
            "plannings/create_plannings.html",
            forms=active_forms,
            assignable_users=assignable_users
        )
    
    # POST logic
    data = request.get_json() if wants_json() else request.form
    client_name = data.get("client_name")
    form_id = data.get("form_id")
    records = data.get("records", [])

    if not client_name or not form_id:
        if wants_json():
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        flash("El nombre del cliente y la selección del formulario son obligatorios.", "error")
        return redirect(url_for("plannings.create_planning"))

    try:
        planning = Planning(
            id=str(uuid.uuid4()),
            planner_id=g.user.id,
            form_id=form_id,
            client_name=client_name,
            status="uploaded",
            total_tasks=len(records),
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(planning)
        
        for record in records:
            # Extract worker_id if provided in the record row
            task_worker_id = record.pop('worker_id', None)
            
            task = Task(
                id=str(uuid.uuid4()),
                planning_id=planning.id,
                form_id=form_id, 
                record_data=record,
                worker_id=task_worker_id,
                status="pending",
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(task)
            
        db.session.commit()
        
        if wants_json():
            return jsonify({"success": True, "id": planning.id})
        
        flash("Planificación creada exitosamente.", "success")
        return redirect(url_for("plannings.list_plannings"))
        
    except Exception as e:
        db.session.rollback()
        if wants_json():
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("plannings.create_planning"))

@bp.route("/<planning_id>")
@login_required
@planning_access_required
def get_planning(planning_id):
    """
    View details of a specific planning.
    """
    planning = check_planning_access(planning_id)
    
    if wants_json():
        return jsonify({
            "success": True,
            "planning": {
                "id": planning.id,
                "client_name": planning.client_name,
                "form_version": planning.form.display_name,
                "status": planning.status,
                "tasks_count": len(planning.tasks)
            }
        })
    
    return render_template(
        "plannings/view_planning.html",
        planning=planning
    )