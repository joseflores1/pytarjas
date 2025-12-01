# pytarjas/blueprints/artifacts/tasks.py
"""
Tasks API blueprint for managing documents/tasks.

Updates:
- Implemented enhanced filtering options for all common fields (timestamps, sync status, form name).
- Added override edit permission for Admin/Planner roles in get_task and update_task.
- Included full response data and form structure in list_tasks output for table view.
- RE-INTRODUCED all synchronization-related fields and filters.
"""

from flask import Blueprint, request, jsonify, render_template, g, abort, redirect, url_for, flash
from datetime import datetime, timezone
from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db
from pytarjas.models.docs_models import Document, Form
from pytarjas.helper import wants_json, save_file_to_disk # Correct helper imports
import uuid
from sqlalchemy import cast, Date, or_ # Explicit import for date filtering
from sqlalchemy.orm import joinedload # Ensure joinedload is imported if needed in get_task

# Create blueprint with URL prefix /tasks
bp = Blueprint("tasks", __name__, url_prefix="/tasks")


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
        
    # Create the document
    document = Document(
        id=str(uuid.uuid4()),
        planning_id=None,
        form_id=form_id,
        record_data=record_data, 
        worker_id=worker_id,
        created_by_id=g.user.id,
        status="pending",
        responses={},
        photos=[],
        is_synced=True,
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(document)
        db.session.commit()
        
        if wants_json():
            return jsonify({
                "success": True,
                "message": "Task created successfully",
                "task_id": document.id
            }), 201
        else:
            flash("Tarea creada exitosamente", "success")
            # CHANGE: Redirect to list_tasks instead of get_task for better flow
            return redirect(url_for("tasks.list_tasks"))
    
    except Exception as e:
        db.session.rollback()
        return (jsonify({"success": False, "error": str(e)}), 500) if wants_json() else abort(500)


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
    query = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions),
        db.joinedload(Document.planning),
        db.joinedload(Document.worker),
        db.joinedload(Document.created_by)
    )
    
    # --- Role-based Access Control (Initial Filter) ---
    if g.user.role == "worker":
        # Workers ONLY see tasks assigned to them OR created by them
        query = query.filter(
            or_(
                Document.worker_id == g.user.id,
                Document.created_by_id == g.user.id
            )
        )

    # --- Specific Filter Application (Applies AFTER Role Control) ---
    if status != 'all':
        query = query.filter(Document.status == status)

    # 1. Assigned To Filter (worker_id): Only available to Admin/Planner
    if g.user.role in ["planner", "admin"] and worker_id_filter:
        query = query.filter(Document.worker_id == worker_id_filter)
    
    # 2. Created By Filter (created_by_id): Available to Admin/Planner/Worker
    if created_by_id_filter:
        query = query.filter(Document.created_by_id == created_by_id_filter)
    
    # 3. Form Filters (Priority: form_id_filter)
    if form_id_filter:
        query = query.filter(Document.form_id == form_id_filter)
    elif form_type_filter:
        query = query.join(Document.form).filter(Form.form_type == form_type_filter)

    # 4. Search Filters (Legacy/Text Search)
    if worker_username_search:
        query = query.join(Document.worker).filter(
            User.username.ilike(f'%{worker_username_search}%')
        )
        
    if form_name_search:
        query = query.join(Document.form).filter(Form.name.ilike(f'%{form_name_search}%'))

    # 5. DYNAMIC QUESTION FILTERS (CRITICAL FIX: Filtering logic was simplified and correctly applied)
    for key, value in dynamic_filters.items():
        if not value:
            continue
            
        # Dynamic filter keys are either 'q_<question_id>' (for responses)
        # or 'q_record_<field_name>' (for record_data, like client_name or container_number)
        
        # NOTE: This dynamic filtering correctly relies on the value being a partial match (%value%)
        if key.startswith('q_record_'):
             record_field = key[9:] 
             # Fix: Ensure JSON string extraction works before applying LIKE
             query = query.filter(
                 Document.record_data.op('->>')(record_field).ilike(f'%{value}%')
             )
        else:
             question_id = key[2:] 
             # Fix: Ensure JSON string extraction works before applying LIKE
             query = query.filter(
                 Document.responses.op('->>')(question_id).ilike(f'%{value}%')
             )


    # RE-INTRODUCED SYNC FILTER
    if is_synced_filter is not None and is_synced_filter != '':
        is_synced_bool = is_synced_filter.lower() == 'true'
        query = query.filter(Document.is_synced == is_synced_bool)

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

    query = apply_timestamp_filter(query, Document.created_at, created_at_min, created_at_max)
    query = apply_timestamp_filter(query, Document.updated_at, updated_at_min, updated_at_max)
    query = apply_timestamp_filter(query, Document.started_at, started_at_min, started_at_max)
    query = apply_timestamp_filter(query, Document.completed_at, completed_at_min, completed_at_max)
    query = apply_timestamp_filter(query, Document.reviewed_at, reviewed_at_min, reviewed_at_max)
    query = apply_timestamp_filter(query, Document.synced_at, synced_at_min, synced_at_max)
        
    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    tasks = []
    for doc in documents:
        # Structure of Questions for the collapsible row
        form_questions = []
        if doc.form and doc.form.questions:
            # Sort questions by order for correct display
            for q in sorted(doc.form.questions, key=lambda x: x.order):
                form_questions.append({
                    "id": q.id,
                    "text": q.question_text,
                    "type": q.question_type,
                    "is_required": q.is_required,
                })

        # Extract a few key fields from record_data for table view preview
        record_preview = {}
        if doc.record_data:
            if 'container_number' in doc.record_data:
                record_preview['Contenedor'] = doc.record_data['container_number']
            if 'ship_name' in doc.record_data:
                record_preview['Nave'] = doc.record_data['ship_name']
            if 'client_name' in doc.record_data and 'Contenedor' not in record_preview:
                record_preview['Cliente'] = doc.record_data['client_name']
        
        task_data = {
            "id": doc.id,
            "record_data": doc.record_data or {},
            "record_preview": record_preview, 
            "status": doc.status,
            "worker": {"username": doc.worker.username, "id": doc.worker.id} if doc.worker else None,
            "created_by": {"username": doc.created_by.username, "id": doc.created_by.id} if doc.created_by else None,
            "form_type": doc.form.form_type if doc.form else "Unknown",
            "form_name": doc.form.name if doc.form else "Deleted Form",
            "responses": doc.responses or {}, 
            "form_questions": form_questions, 
            "is_synced": doc.is_synced, 
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "started_at": doc.started_at.isoformat() if doc.started_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "synced_at": doc.synced_at.isoformat() if doc.synced_at else None, 
            "_document": doc
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
        # Clean tasks data for JSON output (remove _document which is for internal use)
        json_tasks = [{k: v for k, v in t.items() if k != '_document'} for t in tasks]
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


@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    """
    Display a single task for viewing and editing.
    """
    # Load task with necessary relationships
    document = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions),
        db.joinedload(Document.worker),
    ).get(task_id)

    if not document:
        return (jsonify({"success": False, "error": "Task not found"}), 404) if wants_json() else abort(404)

    # --- CRITICAL DATA INTEGRITY CHECK (FIXED ATTRIBUTE NAME) ---
    if document.form and document.form.questions:
        for question in document.form.questions:
            # FIX: Changed 'question.type' to 'question.question_type'
            if not isinstance(question.question_type, str) or len(question.question_type.strip()) == 0:
                error_msg = (
                    f"Data Integrity Error: Question ID {question.id} ('{question.question_text}') "
                    f"in Form '{document.form.name}' has invalid or empty type. "
                    f"Please update the database record for this question."
                )
                print(f"!!! DIAGNOSTIC FAILURE: {error_msg}")
                return (jsonify({"success": False, "error": error_msg}), 500) if wants_json() else abort(500, description=error_msg)
    # --- END DATA INTEGRITY CHECK ---

    # Permission Check: Who can edit/view this?
    is_admin_or_planner = g.user.role in ["admin", "planner"]
    can_override_edit = is_admin_or_planner
    
    # Basic view access check: worker is assigned, worker is creator, or user is admin/planner
    has_view_access = (document.worker_id == g.user.id or 
                       document.created_by_id == g.user.id or 
                       is_admin_or_planner)
    
    if not has_view_access:
        return (jsonify({"success": False, "error": "Access denied"}), 403) if wants_json() else abort(403)

    if wants_json():
        # Minimal JSON response for viewing, if needed by the client
        return jsonify({
            "success": True,
            "task_id": document.id,
            "status": document.status,
            "form_name": document.form.name if document.form else "Deleted Form",
            "responses": document.responses,
            "can_override_edit": can_override_edit
        }), 200
    else:
        # Fetch clients for the client_select input (Placeholder: Assuming all users with 'client' role)
        all_clients = User.query.filter_by(role='client').order_by(User.username).all()

        return render_template(
            "tasks/task_detail.html",
            task=document,
            user=g.user,
            can_override_edit=can_override_edit, # Pass the flag directly
            all_clients=all_clients 
        )


@bp.route("/<task_id>/update", methods=["PUT", "PATCH", "POST"])
@login_required
@task_access_required
def update_task(task_id):
    document = Document.query.get(task_id)
    if not document:
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    is_admin_or_planner = g.user.role in ["admin", "planner"]
    is_finalized = document.status in ["completed", "reviewed", "approved"]
    
    if g.user.role == "worker" and document.worker_id != g.user.id and not is_admin_or_planner:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    if is_finalized and not is_admin_or_planner:
        return jsonify({"success": False, "error": f"Task is already {document.status}. Only Admins or Planners can modify finalized tasks."}), 403
    
    
    # ------------------------------------------------------------------------
    # FILE UPLOAD HANDLING (POST/MULTIPART-FORM-DATA) - FIX APPLIED HERE
    # ------------------------------------------------------------------------
    if request.method == 'POST' and (request.files or request.form):
        
        # 1. Start with existing responses/status from the database
        responses = document.responses if document.responses is not None else {}
        files_uploaded = False
        old_status = document.status

        # 2. Process non-file form data (including any text/radio answers submitted along with the file)
        for key, value in request.form.items():
            if key.startswith('response_'):
                question_id = key.replace('response_', '')
                # Only update with non-empty values (to preserve existing responses/paths if the field was skipped)
                if value.strip() != '':
                     responses[question_id] = value.strip()
        
        # 3. Process uploaded files (overwriting the corresponding entry in responses)
        for key, file in request.files.items():
            if key.startswith('response_') and file.filename != '':
                # Use imported helper function to save the file
                saved_path = save_file_to_disk(file)
                if saved_path:
                    question_id = key.replace('response_', '')
                    # Store the new path/URL (this is the desired behavior for upload/replace)
                    responses[question_id] = saved_path
                    files_uploaded = True
                else:
                    flash("Error al subir el archivo. Verifique el tamaño/formato.", "error")
                    # No need to return error immediately, continue processing other fields/files

        # 4. Handle embedded status change
        status_from_post = request.form.get("status")
        
        # 5. Update Document object (if any file/data was processed or status changed)
        if files_uploaded or status_from_post or any(k.startswith('response_') and v.strip() for k, v in request.form.items()):
            
            document.responses = responses 
            
            # Status change logic (kept as is)
            if status_from_post and status_from_post != old_status:
                document.status = status_from_post
                if status_from_post == "in_progress" and old_status == "pending":
                    if not document.worker_id:
                        document.worker_id = g.user.id
                    if not document.started_at:
                        document.started_at = datetime.now(timezone.utc)
                elif status_from_post == "completed":
                    if not document.completed_at:
                        document.completed_at = datetime.now(timezone.utc)
            
            document.updated_at = datetime.now(timezone.utc)
            
            try:
                db.session.commit()
                # SUCCESS: Reload is required on the client side after this POST
                return jsonify({
                    "success": True, 
                    "message": "Files uploaded and task updated successfully",
                    "status_changed": status_from_post is not None
                }), 200
            except Exception as e:
                db.session.rollback()
                return jsonify({"success": False, "error": str(e)}), 500
                
        # If no files, no status change, and no non-file form data was submitted 
        return jsonify({"success": False, "message": "No changes to save"}), 200

    
    # ------------------------------------------------------------------------
    # JSON DATA HANDLING (PATCH/PUT) - For text/status updates without files
    # ------------------------------------------------------------------------
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required for non-file updates"}), 400
        
    data = request.get_json()
    old_status = document.status
    
    if "status" in data:
        new_status = data["status"]
        document.status = new_status
        
        # Logic for setting timestamps based on status transitions
        if new_status == "in_progress" and old_status == "pending":
            if not document.worker_id:
                document.worker_id = g.user.id
            if not document.started_at:
                document.started_at = datetime.now(timezone.utc)
        elif new_status == "completed":
            if not document.completed_at:
                document.completed_at = datetime.now(timezone.utc)
        
    
    if "responses" in data:
        if document.responses is None:
            document.responses = {}
        
        # CRITICAL FIX: Filter out empty string values from the JSON update payload.
        # This prevents the client-side form submission from overwriting saved file paths 
        # (or other empty inputs) with null/empty strings.
        filtered_responses = {
            k: v for k, v in data["responses"].items() if v is not None and v != ""
        }
        
        document.responses.update(filtered_responses)
        
        # Use explicit SQLAlchemy update call to force JSON field modification detection
        db.session.query(Document).filter_by(id=task_id).update(
            {"responses": document.responses}, synchronize_session=False
        )
    
    if "photos" in data:
        if document.photos is None:
            document.photos = []
        document.photos.extend(data["photos"])
        db.session.query(Document).filter_by(id=task_id).update(
            {"photos": document.photos}, synchronize_session=False
        )
        
    document.updated_at = datetime.now(timezone.utc)
    document.is_synced = data.get("mark_synced", False)
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500