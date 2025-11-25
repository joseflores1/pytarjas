# pytarjas/tasks.py
"""
Tasks API blueprint for managing documents/tasks.

Updates:
- Implemented enhanced filtering options for all common fields (timestamps, sync status, form name).
- Added override edit permission for Admin/Planner roles in get_task and update_task.
- Included full response data and form structure in list_tasks output for table view.
- RE-INTRODUCED all synchronization-related fields (is_synced, synced_at) into list_tasks.
"""

from flask import Blueprint, request, jsonify, render_template, g, abort, redirect, url_for, flash
from datetime import datetime, timezone
from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db
from pytarjas.models.docs_models import Document, Form
from pytarjas.helper import wants_json
import uuid
from sqlalchemy import cast, Date, or_ # Explicit import for date filtering

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
    
    # Validation
    if not form_id:
        return (jsonify({"success": False, "error": "Form is required"}), 400) if wants_json() else abort(400)
    
    form = Form.query.filter_by(id=form_id, is_active=True).first()
    if not form:
        return (jsonify({"success": False, "error": "Form not found"}), 404) if wants_json() else abort(404)
    
    if not worker_id:
        worker_id = g.user.id
    
    # Create the document
    document = Document(
        id=str(uuid.uuid4()),
        planning_id=None,
        form_id=form_id,
        record_data={},
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
    Get list of tasks with role-based filtering.
    
    UPDATES:
    - RE-INTRODUCED sync related fields and filters into context.
    """
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    worker_id_filter = request.args.get('worker_id')
    
    # EXISTING FILTERS
    form_type_filter = request.args.get('form_type')
    container_number_search = request.args.get('container_number', '').strip()
    worker_username_search = request.args.get('worker_username', '').strip()

    # COMMON FIELD FILTERS
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
    
    # RE-INTRODUCED SYNC FILTERS
    synced_at_min = request.args.get('synced_at_min')
    synced_at_max = request.args.get('synced_at_max')
    is_synced_filter = request.args.get('is_synced')
    
    # Build base query
    query = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions), # Eagerly load questions for Q&A view
        db.joinedload(Document.planning),
        db.joinedload(Document.worker),
        db.joinedload(Document.created_by) # Load created_by for the table
    )
    
    # Role-based filtering
    if g.user.role == "worker":
        query = query.filter(
            or_(
                Document.worker_id == g.user.id,
                Document.created_by_id == g.user.id
            )
        )
    elif g.user.role in ["planner", "admin"]:
        if worker_id_filter:
            query = query.filter(Document.worker_id == worker_id_filter)
    
    if status != 'all':
        query = query.filter(Document.status == status)

    # Apply EXISTING Filters
    if form_type_filter:
        query = query.join(Document.form).filter(Form.form_type == form_type_filter)

    if container_number_search:
        # Check for non-empty string and apply filter
        query = query.filter(
            Document.record_data.op('->>')('container_number').ilike(f'%{container_number_search}%')
        )
        
    if worker_username_search:
        # We explicitly join to avoid issues with joinedload
        query = query.join(Document.worker).filter(
            User.username.ilike(f'%{worker_username_search}%')
        )
        
    # Apply NEW Filters (Common Fields)
    if form_name_search:
        query = query.join(Document.form).filter(Form.name.ilike(f'%{form_name_search}%'))

    # RE-INTRODUCED SYNC FILTER
    if is_synced_filter is not None and is_synced_filter != '':
        is_synced_bool = is_synced_filter.lower() == 'true'
        query = query.filter(Document.is_synced == is_synced_bool)

    # --- TIMESTAMP FILTERS (created_at, updated_at, started_at, completed_at, reviewed_at, synced_at) ---
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
    # RE-INTRODUCED
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
            "is_synced": doc.is_synced, # RE-INTRODUCED
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "started_at": doc.started_at.isoformat() if doc.started_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            "synced_at": doc.synced_at.isoformat() if doc.synced_at else None, # RE-INTRODUCED
            "_document": doc
        }
        tasks.append(task_data)
    
    # Get all forms and workers for the UI filters
    all_forms = Form.query.order_by(Form.name).all()
    all_workers = User.query.filter(User.role == 'worker').order_by(User.username).all()
    
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
        form_type_filter=form_type_filter,
        all_workers=all_workers,
        worker_username_filter=worker_username_search, 
        container_number_search=container_number_search,
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
    )


@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    document = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions),
        db.joinedload(Document.planning),
        db.joinedload(Document.worker)
    ).filter_by(id=task_id).first()  

    if not document:
        return (jsonify({"success": False, "error": "Task not found"}), 404) if wants_json() else abort(404)
    
    # Role-based check for override edit permission
    can_override_edit = g.user.role in ["admin", "planner"]
    
    # Worker can only view their own tasks (unless they are admin/planner)
    if g.user.role == "worker" and document.worker_id != g.user.id and not can_override_edit:
        return (jsonify({"success": False, "error": "Access denied"}), 403) if wants_json() else abort(403)
    
    questions = []
    # Handle case where form might have been deleted/detached (unlikely but safe)
    if document.form:
        for q in sorted(document.form.questions, key=lambda x: x.order):
            questions.append({
                "id": q.id,
                "text": q.question_text,
                "type": q.question_type,
                "is_required": q.is_required,
                "order": q.order,
                "options": q.options or {},
                "_question": q
            })
    
    task_data = {
        "id": document.id,
        "status": document.status,
        "record_data": document.record_data or {},
        "form": {
            "id": document.form.id if document.form else None,
            "name": document.form.name if document.form else "Deleted Form",
            "type": document.form.form_type if document.form else "unknown",
            "questions": questions
        },
        "responses": document.responses or {},
        "photos": document.photos or [],
        "worker": {"id": document.worker.id, "username": document.worker.username} if document.worker else None,
        "timestamps": {
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "started_at": document.started_at.isoformat() if document.started_at else None,
            "completed_at": document.completed_at.isoformat() if document.completed_at else None,
            "reviewed_at": document.reviewed_at.isoformat() if document.reviewed_at else None,
            "synced_at": document.synced_at.isoformat() if document.synced_at else None, # LEFT HERE FOR DETAIL VIEW
        },
        "is_synced": document.is_synced, # LEFT HERE FOR DETAIL VIEW
        "can_override_edit": can_override_edit, # NEW FIELD
        "_document": document
    }
    
    if wants_json():
        return jsonify({"success": True, "task": task_data}), 200
    
    # Pass the new flag to the template
    return render_template("tasks/task_detail.html", task=task_data, user=g.user)


@bp.route("/<task_id>/update", methods=["PUT", "PATCH"])
@login_required
@task_access_required
def update_task(task_id):
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required"}), 400
    
    document = Document.query.get(task_id)
    if not document:
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    # Check if worker is attempting to edit a finalized task (completed, reviewed, approved)
    # UNLESS the user is an Admin or Planner (the override edit permission)
    is_admin_or_planner = g.user.role in ["admin", "planner"]
    is_finalized = document.status in ["completed", "reviewed", "approved"]
    
    if g.user.role == "worker" and document.worker_id != g.user.id and not is_admin_or_planner:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    if is_finalized and not is_admin_or_planner:
        # This is the new logic: Admins/Planners can bypass this restriction
        return jsonify({"success": False, "error": f"Task is already {document.status}. Only Admins or Planners can modify finalized tasks."}), 403
    
    data = request.get_json()
    
    if "status" in data:
        new_status = data["status"]
        old_status = document.status
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
        document.responses.update(data["responses"])
        # Use explicit SQLAlchemy update call to force JSON field modification detection
        db.session.query(Document).filter_by(id=task_id).update(
            {"responses": document.responses}, synchronize_session=False
        )
    
    if "photos" in data:
        # For simplicity, we just add new photos, actual PWA logic might replace/manage them better
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