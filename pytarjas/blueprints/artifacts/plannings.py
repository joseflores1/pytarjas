# pytarjas/blueprints/artifacts/plannings.py
"""
Plannings API blueprint for managing work plannings and tasks.

This module defines the resource-centric endpoints /plannings/, /plannings/create, etc.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, g, abort 
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import uuid

# Import database and models
from pytarjas.models.user_models import db, User
from pytarjas.models.docs_models import Planning, Task, Form   

# Import authentication decorators
from pytarjas.auth import login_required, planning_access_required

# Import helper functions
from pytarjas.helper import wants_json

# FIX: Define blueprint for the resource (plannings) with its name/prefix
bp = Blueprint("plannings", __name__, url_prefix="/plannings")


# ============================================================================
# DECORATOR HELPERS (Kept for check_planning_access logic)
# ============================================================================

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
    
    elif g.user.role == "planner" and g.user.id == planning.planner_id:
        return planning
    
    else:
        abort(403)


# ============================================================================
# ROUTE: List all plannings (The resource index: GET /plannings/)
# ============================================================================

@bp.route("/", methods=["GET"]) # FIX: Map to root /
@login_required
@planning_access_required
def list_plannings():
    """
    List all plannings (The default view for /plannings/).
    """
    status_filter = request.args.get('status', 'all')
    planner_id_filter = request.args.get('planner_id')
    form_id_filter=request.args.get("form_id")
    client_name_search = request.args.get('client_name', '').strip()
    form_type_filter = request.args.get('form_type')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    query = Planning.query.options(
        joinedload(Planning.planner),
        joinedload(Planning.form),
        joinedload(Planning.tasks)
    )
    
    if status_filter != 'all':
        query = query.filter(Planning.status == status_filter)
    
    if planner_id_filter and g.user.role in ['admin', 'planner']:
        query = query.filter(Planning.planner_id == planner_id_filter)
    
    if client_name_search:
        query = query.filter(Planning.client_name.ilike(f'%{client_name_search}%'))
    
    if form_type_filter:
        query = query.join(Form).filter(Form.form_type == form_type_filter)
    
    if form_id_filter:
        query = query.filter(Planning.form_id == form_id_filter)

    total = query.count()
    
    plannings = query.order_by(
        Planning.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    plannings_data = []
    for plan in plannings:
        completed_tasks = sum(
            1 for task in plan.tasks 
            if task.status == 'completed'
        )
        
        plan_dict = {
            "id": plan.id,
            "client_name": plan.client_name,
            "form_name": plan.form.name if plan.form else None,
            "form_type": plan.form.form_type if plan.form else None,
            "status": plan.status,
            "total_tasks": plan.total_tasks,
            "completed_tasks": completed_tasks,
            "planner": {
                "id": plan.planner.id,
                "username": plan.planner.username
            } if plan.planner else None,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "_planning": plan
        }
        plannings_data.append(plan_dict)
    
    if wants_json():
        return jsonify({
            "success": True,
            "plannings": plannings_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "status": status_filter if status_filter != 'all' else None,
                "planner_id": planner_id_filter,
                "client_name": client_name_search if client_name_search else None,
                "form_type": form_type_filter
            }
        }), 200
    
    planners = []
    if g.user.role in ['admin', 'planner']:
        planners = User.query.filter_by(role='planner').all()
    
    form_types = db.session.query(Form.form_type).distinct().all()
    form_types = [ft[0] for ft in form_types if ft[0]]
    
    return render_template(
        "plannings/list_plannings.html", # FIX: Changed path from "planner/list_plannings.html"
        plannings=plannings_data,
        total=total,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        planner_id_filter=planner_id_filter,
        client_name_search=client_name_search,
        form_type_filter=form_type_filter,
        planners=planners,
        form_types=form_types,
        user=g.user
    )


# ============================================================================
# ROUTE: Get single planning with details (GET /plannings/<id>)
# ============================================================================

@bp.route("/<planning_id>", methods=["GET"])
@login_required
@planning_access_required
def get_planning(planning_id):
    planning = check_planning_access(planning_id)
    
    progress = {
        "total": planning.total_tasks,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "reviewed": 0,
        "approved": 0
    }
    
    for task in planning.tasks:
        status = task.status
        if status in progress:
            progress[status] += 1
        else:
            progress["pending"] += 1
    
    tasks_data = []
    for task in planning.tasks:
        task_dict = {
            "id": task.id,
            "record_data": task.record_data,
            "status": task.status,
            "worker": {
                "id": task.worker.id,
                "username": task.worker.username
            } if task.worker else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "is_synced": task.is_synced,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        
        tasks_data.append(task_dict)
    
    if wants_json():
        return jsonify({
            "success": True,
            "planning": {
                "id": planning.id,
                "client_name": planning.client_name,
                "status": planning.status,
                "total_tasks": planning.total_tasks,
                "file_name": planning.file_name if planning.file_name else None,
                "form": {
                    "id": planning.form.id,
                    "name": planning.form.name,
                    "form_type": planning.form.form_type,
                    "description": planning.form.description,
                    "questions": [
                        {
                            "id": q.id,
                            "question_text": q.question_text,
                            "question_type": q.question_type,
                            "is_required": q.is_required,
                            "order": q.order,
                            "options": q.options
                        }
                        for q in sorted(planning.form.questions, key=lambda x: x.order)
                    ]
                } if planning.form else None,
                "tasks": tasks_data,
                "planner": {
                    "id": planning.planner.id,
                    "username": planning.planner.username,
                    "email": planning.planner.email
                } if planning.planner else None,
                "progress": progress,
                "created_at": planning.created_at.isoformat() if planning.created_at else None,
                "updated_at": planning.updated_at.isoformat() if planning.updated_at else None
            }
        }), 200
    
    # NOTE: This uses the existing placeholder template name
    return render_template(
        "planner/view_planning.html",
        planning=planning,
        tasks=tasks_data,
        progress=progress,
        user=g.user
    )


# ============================================================================
# ROUTE: Create new planning (GET/POST /plannings/create)
# ============================================================================

@bp.route("/create", methods=["GET", "POST"])
@login_required
@planning_access_required
def create_planning():
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can create plannings."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            # FIX: Redirect to the resource index
            return redirect(url_for("plannings.list_plannings"))
    
    if request.method == "GET":
        if wants_json():
            active_forms = Form.query.filter_by(is_active=True).all()
            return jsonify({
                "success": True,
                "available_forms": [
                    {
                        "id": form.id,
                        "name": form.name,
                        "form_type": form.form_type,
                        "description": form.description
                    }
                    for form in active_forms
                ]
            }), 200
        else:
            active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
            return render_template(
                "planner/create_planning.html",
                forms=active_forms,
                user=g.user
            )
    
    error = None
    
    if wants_json():
        data = request.get_json()
        client_name = data.get("client_name", "").strip()
        form_id = data.get("form_id")
        records_data = data.get("records", [])
        status = data.get("status", "uploaded")
    else:
        client_name = request.form.get("client_name", "").strip()
        form_id = request.form.get("form_id")
        status = request.form.get("status", "uploaded")
        
        records_data = []
        record_index = 0
        
        while True:
            record_field_key = f"record_{record_index}_data"
            
            if record_field_key not in request.form:
                break
            
            record_data = {}
            prefix = f"record_{record_index}_"
            
            for key in request.form.keys():
                if key.startswith(prefix):
                    field_name = key[len(prefix):]
                    record_data[field_name] = request.form.get(key)
            
            if record_data:
                records_data.append(record_data)
            
            record_index += 1
    
    if not client_name:
        error = "Client name is required."
    elif not form_id:
        error = "Form selection is required."
    elif not records_data or len(records_data) == 0:
        error = "At least one record is required."
    else:
        form = Form.query.filter_by(id=form_id, is_active=True).first()
        if not form:
            error = "Form not found or inactive."
    
    if error is None:
        try:
            planning = Planning(
                id=str(uuid.uuid4()),
                planner_id=g.user.id,
                form_id=form_id,
                client_name=client_name,
                status=status,
                total_tasks=len(records_data),
                file_path="",
                file_name="",
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(planning)
            
            created_tasks = []
            for record_data in records_data:
                # FIX: Removed 'photos=[]' argument as the field was removed from the Task model
                task = Task(
                    id=str(uuid.uuid4()),
                    planning_id=planning.id,
                    form_id=form_id,
                    record_data=record_data,
                    created_by_id=g.user.id,
                    worker_id=None,
                    status="pending",
                    responses={},
                    is_synced=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(task)
                created_tasks.append(task)
            
            planning.total_tasks = len(records_data)
            planning.status = "completed"
            planning.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            success_message = (
                f"Planning created successfully with {len(records_data)} tasks."
            )
            
            if wants_json():
                return jsonify({
                    "success": True,
                    "message": success_message,
                    "planning": {
                        "id": planning.id,
                        "client_name": planning.client_name,
                        "total_tasks": planning.total_tasks,
                        "status": planning.status,
                        "created_at": planning.created_at.isoformat()
                    }
                }), 201
            else:
                flash(success_message, "success")
                # FIX: Use correct endpoint name for redirect
                return redirect(url_for("plannings.get_planning", planning_id=planning.id))
        
        except Exception as e:
            db.session.rollback()
            error = f"An error occurred while creating planning: {str(e)}"
    
    if wants_json():
        return jsonify({
            "success": False,
            "error": error
        }), 400
    else:
        flash(error, "error")
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        return render_template(
            "planner/create_planning.html",
            forms=active_forms,
            user=g.user,
            error=error
        )


# ============================================================================
# ROUTE: Delete planning (POST/DELETE /plannings/<id>/delete)
# ============================================================================

@bp.route("/<planning_id>/delete", methods=["POST", "DELETE"])
@login_required
@planning_access_required
def delete_planning(planning_id):
    if g.user.role not in ['planner', 'admin']:
        error_msg = "Access denied. Only planners and admins can delete plannings."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            # FIX: Redirect to the resource index
            return redirect(url_for("plannings.list_plannings"))
    
    planning = check_planning_access(planning_id)
    
    if g.user.role == 'planner' and planning.planner_id != g.user.id:
        error_msg = "Access denied. You can only delete plannings you created."
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 403
        else:
            flash(error_msg, "error")
            # FIX: Redirect to the resource index
            return redirect(url_for("plannings.list_plannings"))
    
    try:
        planning.status = "deleted"
        planning.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        success_message = f"Planning '{planning.client_name}' deleted successfully."
        
        if wants_json():
            return jsonify({
                "success": True,
                "message": success_message
            }), 200
        else:
            flash(success_message, "success")
            # FIX: Redirect to the resource index
            return redirect(url_for("plannings.list_plannings"))
    
    except Exception as e:
        db.session.rollback()
        error_message = f"An error occurred: {str(e)}"
        
        if wants_json():
            return jsonify({
                "success": False,
                "error": error_message
            }), 500
        else:
            flash(error_message, "error")
            # FIX: Redirect to the resource index
            return redirect(url_for("plannings.list_plannings"))


# ============================================================================
# ROUTE: Update planning status (PUT/PATCH /plannings/<id>/status)
# ============================================================================

@bp.route("/<planning_id>/status", methods=["PUT", "PATCH"])
@login_required
@planning_access_required
def update_planning_status(planning_id):
    if g.user.role not in ['planner', 'admin']:
        return jsonify({
            "success": False,
            "error": "Access denied. Only planners and admins can update status."
        }), 403
    
    if not wants_json():
        return jsonify({
            "success": False,
            "error": "This endpoint only accepts JSON requests."
        }), 400
    
    planning = check_planning_access(planning_id)
    
    data = request.get_json()
    new_status = data.get("status")
    
    valid_statuses = ["uploaded", "processing", "completed", "error", "deleted"]
    if not new_status or new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400
    
    try:
        old_status = planning.status
        planning.status = new_status
        planning.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Status updated from '{old_status}' to '{new_status}'.",
            "planning": {
                "id": planning.id,
                "status": planning.status,
                "updated_at": planning.updated_at.isoformat()
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Database error: {str(e)}"
        }), 500