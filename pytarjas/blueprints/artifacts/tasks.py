# pytarjas/blueprints/artifacts/tasks.py
"""
Complete Tasks API blueprint.
Updated to support hybrid metadata: merging predefined planning fields with ad-hoc dynamic fields.
Includes verification logic that persists corrections to task record_data and only triggers once.
"""

from flask import Blueprint, request, jsonify, render_template, g, abort, redirect, url_for, flash, send_file
from datetime import datetime, timezone
import uuid
import io 
import json
from sqlalchemy import cast, Date, or_, Text 
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified

from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db
from pytarjas.models.docs_models import Task, Form, Planning, PlanningTemplate
from pytarjas.helper import wants_json, save_file_to_disk 
from pytarjas.services.pdf_service import generate_tarja_pdf

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

@bp.route("/<task_id>/upload_file", methods=["POST"])
@login_required
@task_access_required
def upload_file_temp(task_id):
    """Handles immediate file upload separately from form data."""
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({"success": False, "error": "No valid file uploaded"}), 400

    file = request.files['file']
    question_id = request.form.get('question_id') 

    if not question_id:
        return jsonify({"success": False, "error": "Missing question ID for file naming."}), 400

    is_admin_or_planner = g.user.role in ["admin", "planner"]
    is_finalized = task.status in ["completed", "reviewed", "approved"]
    
    if is_finalized:
        if not is_admin_or_planner:
            return jsonify({"success": False, "error": "Cannot upload files to finalized task."}), 403

    try:
        saved_path = save_file_to_disk(file, task_id, question_id) 
        if saved_path:
            return jsonify({
                "success": True,
                "message": "File uploaded successfully",
                "path": saved_path
            }), 200
        else:
            raise Exception("File save failed.")
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Upload failed: {str(e)}"}), 500

@bp.route("/create", methods=["GET", "POST"])
@login_required
@task_access_required
def create_task():
    """Create a task with support for hybrid metadata (Planning Template + Ad-hoc)."""
    if request.method == "GET":
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        
        existing_plannings = Planning.query.options(
            joinedload(Planning.form),
            joinedload(Planning.template).joinedload(PlanningTemplate.fields)
        ).order_by(Planning.created_at.desc()).all()

        assignable_users = []
        if g.user.role == "worker":
            assignable_users = [g.user]
        elif g.user.role == "planner":
            assignable_users = User.query.filter(User.role.in_(["worker", "planner"])).order_by(User.username).all()
        elif g.user.role == "admin":
            assignable_users = User.query.filter(User.role.in_(["worker", "planner", "admin"])).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [{"id": f.id, "name": f.display_name} for f in active_forms],
                "plannings": [
                    {
                        "id": p.id, 
                        "client_name": p.client_name, 
                        "form_id": p.form_id,
                        "template": {
                            "id": p.template.id,
                            "fields": [
                                {
                                    "name": f.field_name,
                                    "label": f.field_label,
                                    "type": f.field_type,
                                    "required": f.is_required,
                                    "options": f.options
                                } for f in p.template.fields
                            ]
                        } if p.template else None
                    } for p in existing_plannings
                ],
                "assignable_users": [{"id": u.id, "username": u.username} for u in assignable_users]
            })
        
        return render_template(
            "tasks/create_tasks.html", 
            forms=active_forms, 
            existing_plannings=existing_plannings,
            assignable_users=assignable_users,
            user=g.user
        )
    
    data = request.get_json() if wants_json() else request.form
    form_id = data.get("form_id")
    worker_id = data.get("worker_id") or g.user.id
    planning_id = data.get("planning_id")
    
    record_data = {}
    metadata_values = data.get("metadata_values", {})
    if isinstance(metadata_values, dict):
        record_data.update(metadata_values)

    ad_hoc_definitions = data.get("ad_hoc_metadata", [])
    if not wants_json():
        if isinstance(ad_hoc_definitions, str):
            try:
                ad_hoc_definitions = json.loads(ad_hoc_definitions)
            except json.JSONDecodeError:
                ad_hoc_definitions = []
                
    if isinstance(ad_hoc_definitions, list):
        for item in ad_hoc_definitions:
            key = item.get('key')
            val = item.get('value')
            if key:
                if isinstance(key, str):
                    if key.strip():
                        record_data[key.strip()] = val

    if not form_id:
        if wants_json():
            return jsonify({"success": False, "error": "Form is required"}), 400
        
        abort(400)
    
    task = Task(
        id=str(uuid.uuid4()),
        planning_id=planning_id if planning_id else None,
        form_id=form_id,
        record_data=record_data, 
        worker_id=worker_id,
        created_by_id=g.user.id,
        status="pending",
        responses={},
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(task)
        db.session.commit()
        
        if wants_json():
            return jsonify({"success": True, "task_id": task.id}), 201
            
        flash("Tarea creada exitosamente", "success")
        return redirect(url_for("tasks.list_tasks"))
        
    except Exception as e:
        db.session.rollback()
        if wants_json():
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("tasks.create_task"))

@bp.route("/", methods=["GET"])
@login_required
@task_access_required
def list_tasks():
    """List tasks with advanced filtering."""
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    query = Task.query.options(
        joinedload(Task.form).joinedload(Form.questions),
        joinedload(Task.planning),
        joinedload(Task.worker),
        joinedload(Task.created_by)
    )
    
    if g.user.role == "worker":
        query = query.filter(or_(Task.worker_id == g.user.id, Task.created_by_id == g.user.id))
    elif g.user.role == "client":
        query = query.join(Task.planning).filter(Planning.client_name == g.user.username)

    if status != 'all':
        query = query.filter(Task.status == status)
    
    form_id_filter = request.args.get('form_id_filter')
    if form_id_filter:
        query = query.filter(Task.form_id == form_id_filter)

    created_by_id_filter = request.args.get('created_by_id')
    if created_by_id_filter:
        query = query.filter(Task.created_by_id == created_by_id_filter)

    worker_id_filter = request.args.get('worker_id')
    if worker_id_filter:
        query = query.filter(Task.worker_id == worker_id_filter)

    dynamic_filters = {}
    for key, value in request.args.items():
        if key.startswith('q_'):
            if value:
                question_id = key[2:]
                query = query.filter(cast(Task.responses[question_id], Text).ilike(f"%{value}%"))
                dynamic_filters[key] = value

    def apply_date_filter(q, field, val_min, val_max):
        if val_min:
            try:
                d = datetime.strptime(val_min, '%Y-%m-%d').date()
                q = q.filter(cast(field, Date) >= d)
            except ValueError:
                pass
        
        if val_max:
            try:
                d = datetime.strptime(val_max, '%Y-%m-%d').date()
                q = q.filter(cast(field, Date) <= d)
            except ValueError:
                pass
        
        return q

    created_at_min = request.args.get('created_at_min')
    created_at_max = request.args.get('created_at_max')
    query = apply_date_filter(query, Task.created_at, created_at_min, created_at_max)
    
    started_at_min = request.args.get('started_at_min')
    started_at_max = request.args.get('started_at_max')
    query = apply_date_filter(query, Task.started_at, started_at_min, started_at_max)

    completed_at_min = request.args.get('completed_at_min')
    completed_at_max = request.args.get('completed_at_max')
    query = apply_date_filter(query, Task.completed_at, completed_at_min, completed_at_max)
    
    total = query.count()
    db_tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    
    all_forms = Form.query.order_by(Form.name.asc(), Form.version.desc()).all()
    all_assignable_users = User.query.filter(User.role.in_(["worker", "planner", "admin"])).all()

    return render_template(
        "tasks/list_tasks.html",
        tasks=db_tasks,
        total=total,
        status=status,
        offset=offset,
        limit=limit,
        all_forms=all_forms,
        form_id_filter=form_id_filter,
        created_by_id_filter=created_by_id_filter,
        worker_id_filter=worker_id_filter,
        created_at_min=created_at_min,
        created_at_max=created_at_max,
        started_at_min=started_at_min,
        started_at_max=started_at_max,
        completed_at_min=completed_at_min,
        completed_at_max=completed_at_max,
        all_assignable_users=all_assignable_users,
        all_creators=all_assignable_users,
        user=g.user,
        dynamic_filters=dynamic_filters
    )

@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    """Task detail and filling entry point."""
    task = Task.query.options(
        joinedload(Task.planning),
        joinedload(Task.form).joinedload(Form.questions),
        joinedload(Task.worker)
    ).get_or_404(task_id)

    can_override_edit = g.user.role in ["admin", "planner"]
    all_clients = User.query.filter_by(role='client').all()

    verification_prompts = []
    planning = task.planning
    
    # Logic: Only show verification if the task is still 'pending'
    if planning:
        if planning.verification_config:
            if task.status == "pending":
                for field_name, config in planning.verification_config.items():
                    expected_value = None
                    is_row_field = config.get("is_row_field", False)
                    
                    if is_row_field:
                        expected_value = task.record_data.get(field_name)
                    else:
                        expected_value = planning.metadata_values.get(config.get("label"))

                    if expected_value is not None:
                        verification_prompts.append({
                            "field_name": field_name,
                            "label": config.get("label"),
                            "expected_value": expected_value
                        })
    
    return render_template(
        "tasks/edit_tasks.html", 
        task=task, 
        can_override_edit=can_override_edit, 
        all_clients=all_clients,
        user=g.user,
        verification_prompts=verification_prompts
    )

@bp.route("/<task_id>/update", methods=["PUT", "PATCH"])
@login_required
@task_access_required
def update_task(task_id):
    """Updates task responses, metadata verifications, and status."""
    task = Task.query.get_or_404(task_id)
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required"}), 400
        
    data = request.get_json()
    is_admin = g.user.role in ["admin", "planner"]
    
    if task.status in ["completed", "reviewed", "approved"]:
        if not is_admin:
            return jsonify({"success": False, "error": "Task is finalized"}), 403
    
    # PERSISTENCE: Save worker corrections to the actual task record_data
    if "verifications" in data:
        verifications = data["verifications"]
        for field_name, v_info in verifications.items():
            if not v_info.get("matches"):
                actual_val = v_info.get("actual_value")
                if actual_val:
                    task.record_data[field_name] = actual_val
        
        flag_modified(task, "record_data")

    if "status" in data:
        new_status = data["status"]
        if new_status == "in_progress":
            if task.status == "pending":
                task.started_at = datetime.now(timezone.utc)
        elif new_status == "completed":
            task.completed_at = datetime.now(timezone.utc)
        task.status = new_status
        
    if "responses" in data:
        task.responses = data["responses"]
        flag_modified(task, "responses")
    
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"success": True})

@bp.route("/<task_id>/pdf")
@login_required
@task_access_required
def download_task_pdf(task_id):
    """Generates and downloads the task tarja PDF."""
    task = Task.query.get_or_404(task_id)
    try:
        pdf_bytes = generate_tarja_pdf(task)
        filename = f"Tarja_{task.id[:8]}.pdf"
        return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f"Error al generar PDF: {str(e)}", "error")
        return redirect(url_for('tasks.get_task', task_id=task.id))