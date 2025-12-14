# pytarjas/blueprints/artifacts/tasks.py
"""
Tasks API blueprint for managing tasks.

Updates:
- Implemented enhanced filtering options for all common fields (timestamps, sync status, form name).
- Added override edit permission for Admin/Planner roles in get_task and update_task.
- Included full response data and form structure in list_tasks output for table view.
- RADICAL FIX: Implemented decoupled, multi-file upload via /upload_file endpoint (POST) for preserving file history.
- The main task update is now strictly JSON (PATCH), accepting file paths as array elements in the 'responses' object.
- BUG FIX: Fixed variable shadowing in list_tasks that prevented tasks from displaying.
- BUG FIX: Fixed JSON saving issue in update_task by using flag_modified instead of invalid bulk update.
"""

from flask import Blueprint, request, jsonify, render_template, g, abort, redirect, url_for, flash
from datetime import datetime, timezone
from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db
from pytarjas.models.docs_models import Task, Form
# NOTE: The helper.py file has been modified externally to accept (file, task_id, question_id)
from pytarjas.helper import wants_json, save_file_to_disk 
import uuid
from sqlalchemy import cast, Date, or_ 
from sqlalchemy.orm import joinedload
# NEW IMPORT: Required to properly track changes in JSON columns
from sqlalchemy.orm.attributes import flag_modified

# Create blueprint with URL prefix /tasks
bp = Blueprint("tasks", __name__, url_prefix="/tasks")


# --- NEW: Multi-File Upload Endpoint ---
@bp.route("/<task_id>/upload_file", methods=["POST"])
@login_required
@task_access_required
def upload_file_temp(task_id):
    """
    Handles immediate file upload (AJAX call) separately from form data.
    Saves the file using a unique name based on Task ID, Question ID, and UUID 
    to preserve file history and context.
    """
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    # Check for file input named 'file' and required metadata
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({"success": False, "error": "No valid file uploaded"}), 400

    file = request.files['file']
    # Extract question_id from the FormData payload (sent by JS)
    question_id = request.form.get('question_id') 

    if not question_id:
        return jsonify({"success": False, "error": "Missing question ID for file naming."}), 400

    is_admin_or_planner = g.user.role in ["admin", "planner"]
    is_finalized = task.status in ["completed", "reviewed", "approved"]
    
    if is_finalized and not is_admin_or_planner:
        return jsonify({"success": False, "error": "Cannot upload files to finalized task."}), 403

    try:
        # CRITICAL: Pass task_id and question_id to the helper function
        # The helper now generates a unique filename for history preservation.
        saved_path = save_file_to_disk(file, task_id, question_id) 
        
        if saved_path:
            return jsonify({
                "success": True,
                "message": "File uploaded successfully",
                "path": saved_path
            }), 200
        else:
            raise Exception("File save failed or helper returned empty path.")

    except Exception as e:
        return jsonify({"success": False, "error": f"Upload failed: {str(e)}"}), 500


# --- Task Creation Endpoint (Unchanged) ---
@bp.route("/create", methods=["GET", "POST"])
@login_required
@task_access_required
def create_task():
    """
    Create a standalone task (not from planning).
    """
    if request.method == "GET":
        # Get active forms
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        
        # Get assignable users based on role
        assignable_users = []
        if g.user.role == "worker":
            assignable_users = [g.user]
        elif g.user.role == "planner":
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner"])
            ).order_by(User.username).all()
        elif g.user.role == "admin":
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner", "admin"])
            ).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [{"id": f.id, "name": f.name, "type": f.form_type} for f in active_forms],
                "assignable_users": [{"id": u.id, "username": u.username, "role": u.role} for u in assignable_users]
            }), 200
        else:
            return render_template(
                "tasks/create_task.html",
                forms=active_forms,
                assignable_users=assignable_users,
                user=g.user
            )
    
    # POST: Create the task
    if wants_json():
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    form_id = data.get("form_id")
    worker_id = data.get("worker_id")
    client_name_input = data.get("client_name_input") 

    # Validation
    if not form_id:
        return (jsonify({"success": False, "error": "Form is required"}), 400) if wants_json() else abort(400)
    
    form = Form.query.filter_by(id=form_id, is_active=True).first()
    if not form:
        return (jsonify({"success": False, "error": "Form not found"}), 404) if wants_json() else abort(404)
    
    if not worker_id:
        worker_id = g.user.id
    
    # NEW: Store client_name in record_data if provided
    record_data = {}
    if client_name_input:
        record_data["client_name"] = client_name_input
        
    # Create the task 
    task = Task(
        id=str(uuid.uuid4()),
        planning_id=None,
        form_id=form_id,
        record_data=record_data, 
        worker_id=worker_id,
        created_by_id=g.user.id,
        status="pending",
        responses={},
        # PHOTOS and PDF_PATH are now removed, simplifying schema.
        is_synced=True,
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(task)
        db.session.commit()
        
        if wants_json():
            return jsonify({
                "success": True,
                "message": "Task created successfully",
                "task_id": task.id
            }), 201
        else:
            flash("Tarea creada exitosamente", "success")
            return redirect(url_for("tasks.list_tasks"))
    
    except Exception as e:
        db.session.rollback()
        return (jsonify({"success": False, "error": str(e)}), 500) if wants_json() else abort(500)


# --- Task Listing Endpoint (Unchanged) ---
@bp.route("/", methods=["GET"])
@login_required
@task_access_required
def list_tasks():
    """
    Get list of tasks with role-based filtering and dynamic search fields.
    """
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    # EXISTING & NEW FILTERS
    worker_id_filter = request.args.get('worker_id')
    created_by_id_filter = request.args.get('created_by_id') 
    
    form_type_filter = request.args.get('form_type')
    worker_username_search = request.args.get('worker_username', '').strip() 
    
    # Dropdown Filter
    form_id_filter = request.args.get('form_id_filter') 

    # Dynamic filter (free text search, kept for URL cleanup handling)
    form_name_search = request.args.get('form_name_search', '').strip()
    
    created_at_min = request.args.get('created_at_min')
    created_at_max = request.args.get('created_at_max')
    updated_at_min = request.args.get('updated_at_min')
    updated_at_max = request.args.get('updated_at_max')
    started_at_min = request.args.get('started_at_min')
    started_at_max = request.args.get('started_at_max')
    completed_at_min = request.args.get('completed_at_min')
    completed_at_max = request.args.get('completed_at_max')
    reviewed_at_min = request.args.get('reviewed_at_min')
    reviewed_at_max = request.args.get('reviewed_at_max')
    
    # SYNC FILTERS
    synced_at_min = request.args.get('synced_at_min')
    synced_at_max = request.args.get('synced_at_max')
    is_synced_filter = request.args.get('is_synced')
    
    # DYNAMIC QUESTION FILTERS: Collect all parameters starting with 'q_'
    dynamic_filters = {k: v.strip() for k, v in request.args.items() if k.startswith('q_') and v.strip()}

    # Build base query
    query = Task.query.options(
        db.joinedload(Task.form).joinedload(Form.questions),
        db.joinedload(Task.planning),
        db.joinedload(Task.worker),
        db.joinedload(Task.created_by)
    )
    
    # --- Role-based Access Control (Initial Filter) ---
    if g.user.role == "worker":
        # Workers ONLY see tasks assigned to them OR created by them
        query = query.filter(
            or_(
                Task.worker_id == g.user.id,
                Task.created_by_id == g.user.id
            )
        )

    # --- Specific Filter Application (Applies AFTER Role Control) ---
    if status != 'all':
        query = query.filter(Task.status == status)

    # 1. Assigned To Filter (worker_id): Only available to Admin/Planner
    if g.user.role in ["planner", "admin"] and worker_id_filter:
        query = query.filter(Task.worker_id == worker_id_filter)
    
    # 2. Created By Filter (created_by_id): Available to Admin/Planner/Worker
    if created_by_id_filter:
        query = query.filter(Task.created_by_id == created_by_id_filter)
    
    # 3. Form Filters (Priority: form_id_filter)
    if form_id_filter:
        query = query.filter(Task.form_id == form_id_filter)
    elif form_type_filter:
        query = query.join(Task.form).filter(Form.form_type == form_type_filter)

    # 4. Search Filters (Legacy/Text Search)
    if worker_username_search:
        query = query.join(Task.worker).filter(
            User.username.ilike(f'%{worker_username_search}%')
        )
        
    if form_name_search:
        query = query.join(Task.form).filter(Form.name.ilike(f'%{form_name_search}%'))

    # 5. DYNAMIC QUESTION FILTERS
    for key, value in dynamic_filters.items():
        if not value:
            continue
            
        if key.startswith('q_record_'):
             record_field = key[9:] 
             query = query.filter(
                 Task.record_data.op('->>')(record_field).ilike(f'%{value}%')
             )
        else:
             question_id = key[2:] 
             query = query.filter(
                 Task.responses.op('->>')(question_id).ilike(f'%{value}%')
             )


    # RE-INTRODUCED SYNC FILTER
    if is_synced_filter is not None and is_synced_filter != '':
        is_synced_bool = is_synced_filter.lower() == 'true'
        query = query.filter(Task.is_synced == is_synced_bool)

    # --- TIMESTAMP FILTERS ---
    def apply_timestamp_filter(query, field, min_val, max_val):
        if min_val:
            try:
                min_date = datetime.strptime(min_val, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                query = query.filter(cast(field, Date) >= min_date.date())
            except ValueError:
                pass
        if max_val:
            try:
                max_date = datetime.strptime(max_val, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                query = query.filter(cast(field, Date) <= max_date.date())
            except ValueError:
                pass
        return query

    query = apply_timestamp_filter(query, Task.created_at, created_at_min, created_at_max)
    query = apply_timestamp_filter(query, Task.updated_at, updated_at_min, updated_at_max)
    query = apply_timestamp_filter(query, Task.started_at, started_at_min, started_at_max)
    query = apply_timestamp_filter(query, Task.completed_at, completed_at_min, completed_at_max)
    query = apply_timestamp_filter(query, Task.reviewed_at, reviewed_at_min, reviewed_at_max)
    query = apply_timestamp_filter(query, Task.synced_at, synced_at_min, synced_at_max)
        
    total = query.count()
    # FIX: Renamed variable to avoid shadowing 'tasks' list below
    db_tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    
    tasks = []
    # FIX: Iterating over db_tasks instead of empty tasks list
    for task in db_tasks:
        # Structure of Questions for the collapsible row
        form_questions = []
        if task.form and task.form.questions:
            # Sort questions by order for correct display
            for q in sorted(task.form.questions, key=lambda x: x.order):
                form_questions.append({
                    "id": q.id,
                    "text": q.question_text,
                    "type": q.question_type,
                    "is_required": q.is_required,
                })

        # Extract a few key fields from record_data for table view preview
        record_preview = {}
        if task.record_data:
            if 'container_number' in task.record_data:
                record_preview['Contenedor'] = task.record_data['container_number']
            if 'ship_name' in task.record_data:
                record_preview['Nave'] = task.record_data['ship_name']
            if 'client_name' in task.record_data and 'Contenedor' not in record_preview:
                record_preview['Cliente'] = task.record_data['client_name']
        
        task_data = {
            "id": task.id,
            "record_data": task.record_data or {},
            "record_preview": record_preview, 
            "status": task.status,
            "worker": {"username": task.worker.username, "id": task.worker.id} if task.worker else None,
            "created_by": {"username": task.created_by.username, "id": task.created_by.id} if task.created_by else None,
            "form_type": task.form.form_type if task.form else "Unknown",
            "form_name": task.form.name if task.form else "Deleted Form",
            "responses": task.responses or {}, 
            "form_questions": form_questions, 
            "is_synced": task.is_synced, 
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
            "synced_at": task.synced_at.isoformat() if task.synced_at else None, 
            "_task": task
        }
        tasks.append(task_data)
    
    # Get all forms and assignable users for the UI filters
    all_forms = Form.query.options(joinedload(Form.questions)).order_by(Form.name).all()
    
    # Determine the list of assignable users for the filter dropdown
    assignable_roles = ["worker", "planner"]
    if g.user.role == 'admin':
        assignable_roles = ["admin", "worker", "planner"]
    
    all_assignable_users = User.query.filter(User.role.in_(assignable_roles)).order_by(User.username).all()

    # Determine the list of users who can be set as CREATOR (same set as assignable users, excluding client)
    all_creators = User.query.filter(User.role.in_(assignable_roles)).order_by(User.username).all()

    
    if wants_json():
        # Clean tasks data for JSON output (remove _task which is for internal use)
        json_tasks = [{k: v for k, v in t.items() if k != '_task'} for t in tasks]
        return jsonify({
            "success": True,
            "tasks": json_tasks,
            "total": total
        }), 200
    
    return render_template(
        "tasks/task_list.html",
        tasks=tasks,
        status=status,
        total=total,
        offset=offset,
        limit=limit,
        user=g.user,
        # CONTEXT FOR FILTERS
        all_forms=all_forms,
        all_assignable_users=all_assignable_users,
        all_creators=all_creators, 
        form_id_filter=form_id_filter,
        form_type_filter=form_type_filter,
        worker_id_filter=worker_id_filter, 
        created_by_id_filter=created_by_id_filter, 
        worker_username_filter=worker_username_search, 
        form_name_search=form_name_search,
        created_at_min=created_at_min,
        created_at_max=created_at_max,
        updated_at_min=updated_at_min,
        updated_at_max=updated_at_max,
        started_at_min=started_at_min,
        started_at_max=started_at_max,
        completed_at_min=completed_at_min,
        completed_at_max=completed_at_max,
        reviewed_at_min=reviewed_at_min,
        reviewed_at_max=reviewed_at_max,
        synced_at_min=synced_at_min,
        synced_at_max=synced_at_max,
        is_synced_filter=is_synced_filter,
        # NEW: Pass dynamic filters to pre-fill the form
        dynamic_filters=dynamic_filters
    )


# --- Task Detail Endpoint (Unchanged) ---
@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    """
    Display a single task for viewing and editing.
    """
    # Load task with necessary relationships
    task = Task.query.options(
        db.joinedload(Task.form).joinedload(Form.questions),
        db.joinedload(Task.worker),
    ).get(task_id)

    if not task:
        return (jsonify({"success": False, "error": "Task not found"}), 404) if wants_json() else abort(404)

    # --- CRITICAL DATA INTEGRITY CHECK (FIXED ATTRIBUTE NAME) ---
    if task.form and task.form.questions:
        for question in task.form.questions:
            # FIX: Changed 'question.type' to 'question.question_type'
            if not isinstance(question.question_type, str) or len(question.question_type.strip()) == 0:
                error_msg = (
                    f"Data Integrity Error: Question ID {question.id} ('{question.question_text}') "
                    f"in Form '{task.form.name}' has invalid or empty type. "
                    f"Please update the database record for this question."
                )
                print(f"!!! DIAGNOSTIC FAILURE: {error_msg}")
                return (jsonify({"success": False, "error": error_msg}), 500) if wants_json() else abort(500, description=error_msg)
    # --- END DATA INTEGRITY CHECK ---

    # Permission Check: Who can edit/view this?
    is_admin_or_planner = g.user.role in ["admin", "planner"]
    can_override_edit = is_admin_or_planner
    
    # Basic view access check: worker is assigned, worker is creator, or user is admin/planner
    has_view_access = (task.worker_id == g.user.id or 
                       task.created_by_id == g.user.id or 
                       is_admin_or_planner)
    
    if not has_view_access:
        return (jsonify({"success": False, "error": "Access denied"}), 403) if wants_json() else abort(403)

    if wants_json():
        # Minimal JSON response for viewing, if needed by the client
        return jsonify({
            "success": True,
            "task_id": task.id,
            "status": task.status,
            "form_name": task.form.name if task.form else "Deleted Form",
            "responses": task.responses,
            "can_override_edit": can_override_edit
        }), 200
    else:
        # Fetch clients for the client_select input (Placeholder: Assuming all users with 'client' role)
        all_clients = User.query.filter_by(role='client').order_by(User.username).all()

        return render_template(
            "tasks/task_detail.html",
            task=task,
            user=g.user,
            can_override_edit=can_override_edit, # Pass the flag directly
            all_clients=all_clients 
        )


# --- Task Update Endpoint (Decoupled, JSON/PATCH ONLY) ---
@bp.route("/<task_id>/update", methods=["PUT", "PATCH"])
@login_required
@task_access_required
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    is_admin_or_planner = g.user.role in ["admin", "planner"]
    is_finalized = task.status in ["completed", "reviewed", "approved"]
    
    if g.user.role == "worker" and task.worker_id != g.user.id and not is_admin_or_planner:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    if is_finalized and not is_admin_or_planner:
        return jsonify({"success": False, "error": f"Task is already {task.status}. Only Admins or Planners can modify finalized tasks."}), 403
    
    
    # ------------------------------------------------------------------------
    # JSON DATA HANDLING (PATCH/PUT) - Accepting file path array strings
    # ------------------------------------------------------------------------
    if not request.is_json:
        # File uploads are handled by the dedicated /upload_file endpoint
        return jsonify({"success": False, "error": "JSON required for task update. File uploads must use the dedicated '/upload_file' endpoint."}), 400
        
    data = request.get_json()
    old_status = task.status
    
    if "status" in data:
        new_status = data["status"]
        task.status = new_status
        
        # Logic for setting timestamps based on status transitions
        if new_status == "in_progress" and old_status == "pending":
            if not task.worker_id:
                task.worker_id = g.user.id
            if not task.started_at:
                task.started_at = datetime.now(timezone.utc)
        elif new_status == "completed":
            if not task.completed_at:
                task.completed_at = datetime.now(timezone.utc)
        
    
    if "responses" in data:
        if task.responses is None:
            task.responses = {}
        
        # Responses now include text answers and SAVED FILE PATHS (JSON string arrays)
        task.responses.update(data["responses"])
        
        # FIX: Use flag_modified to notify SQLAlchemy of the JSON change.
        # The previous bulk update using Task.responses (class attribute) was invalid 
        # as it updated the column with itself instead of the new value.
        flag_modified(task, "responses")
    
    task.updated_at = datetime.now(timezone.utc)
    task.is_synced = data.get("mark_synced", False)
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500