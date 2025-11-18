# pytarjas/tasks.py
"""
Tasks API blueprint for managing documents/tasks.

This blueprint provides DUAL-RESPONSE endpoints for CRUD operations on tasks (documents).
It's designed to be used by Workers, Planners, and Admins - each with different permissions.

Key features:
- Role-based access control (workers see their tasks, planners see all, etc.)
- Offline sync support
- DUAL response format: HTML templates OR JSON (based on request headers)
- RESTful design

Response Format Detection:
- JSON: When request has 'Accept: application/json' header or 'Content-Type: application/json'
- HTML: Default for browser requests (clicking links)

Access hierarchy:
- Worker: Can view/update their own assigned tasks
- Planner: Can view/update/assign all tasks
- Admin: Full access to all tasks
- Client: No access to tasks
"""

from flask import Blueprint, request, jsonify, render_template, g, abort
from datetime import datetime, timezone
from pytarjas.auth import login_required, task_access_required
from pytarjas.models.user_models import User, db #noqa
from pytarjas.models.docs_models import Document, Planification, Form, Question #noqa
from pytarjas.helper import wants_json
# Create blueprint with URL prefix /tasks
# This API is shared across worker, planner, and admin interfaces
bp = Blueprint("tasks", __name__, url_prefix="/tasks")



@bp.route("/create", methods=["GET", "POST"])
@login_required
@task_access_required
def create_task():
    """
    Create a standalone task (not from planification).
    
    DUAL RESPONSE ENDPOINT: Returns JSON or HTML based on request headers.
    
    Role-based assignment rules:
    - Worker: Can only assign to themselves
    - Planner: Can assign to themselves or any Worker
    - Admin: Can assign to anyone except other Admins
    
    GET Response:
    Returns available forms and assignable users based on role
    
    POST Request Body (JSON):
    {
        "form_id": "form-uuid",
        "worker_id": "user-uuid",  // Optional, defaults to creator
        "record_data": {  // Optional initial data
            "field1": "value1",
            ...
        }
    }
    
    POST Response (201):
    {
        "success": true,
        "task": {
            "id": "doc-uuid",
            "status": "pending",
            ...
        }
    }
    """
    if request.method == "GET":
        # Get active forms
        active_forms = Form.query.filter_by(is_active=True).order_by(Form.name).all()
        
        # Get assignable users based on role
        assignable_users = []
        if g.user.role == "worker":
            # Workers can only assign to themselves
            assignable_users = [g.user]
        elif g.user.role == "planner":
            # Planners can assign to themselves + workers
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner"])
            ).order_by(User.username).all()
        elif g.user.role == "admin":
            # Admins can assign to anyone except other admins
            assignable_users = User.query.filter(
                User.role.in_(["worker", "planner", "admin"])
            ).order_by(User.username).all()
        
        if wants_json():
            return jsonify({
                "success": True,
                "forms": [
                    {
                        "id": form.id,
                        "name": form.name,
                        "form_type": form.form_type,
                        "description": form.description
                    }
                    for form in active_forms
                ],
                "assignable_users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role
                    }
                    for user in assignable_users
                ]
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
    record_data = data.get("record_data", {})
    
    # Validation
    if not form_id:
        error_msg = "Form is required"
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 400
        else:
            abort(400, description=error_msg)
    
    # Verify form exists and is active
    form = Form.query.filter_by(id=form_id, is_active=True).first()
    if not form:
        error_msg = "Form not found or inactive"
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 404
        else:
            abort(404, description=error_msg)
    
    # Default worker_id to creator if not specified
    if not worker_id:
        worker_id = g.user.id
    
    # Verify assignment permissions
    assignee = User.query.get(worker_id)
    if not assignee:
        error_msg = "Assigned user not found"
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 404
        else:
            abort(404, description=error_msg)
    
    # Check assignment rules
    if g.user.role == "worker":
        # Workers can only assign to themselves
        if worker_id != g.user.id:
            error_msg = "Workers can only assign tasks to themselves"
            if wants_json():
                return jsonify({"success": False, "error": error_msg}), 403
            else:
                abort(403, description=error_msg)
    elif g.user.role == "planner":
        # Planners can assign to workers and themselves
        if assignee.role not in ["worker", "planner"]:
            error_msg = "Planners can only assign to Workers or themselves"
            if wants_json():
                return jsonify({"success": False, "error": error_msg}), 403
            else:
                abort(403, description=error_msg)
    elif g.user.role == "admin":
        # Admins can assign to anyone except other admins
        if assignee.role == "admin" and assignee.id != g.user.id:
            error_msg = "Cannot assign tasks to other Admins"
            if wants_json():
                return jsonify({"success": False, "error": error_msg}), 403
            else:
                abort(403, description=error_msg)
    
    # Create the document
    import uuid
    document = Document(
        id=str(uuid.uuid4()),
        planification_id=None,  # Standalone task
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
                "task": {
                    "id": document.id,
                    "form_id": document.form_id,
                    "worker_id": document.worker_id,
                    "created_by_id": document.created_by_id,
                    "status": document.status,
                    "created_at": document.created_at.isoformat()
                }
            }), 201
        else:
            from flask import redirect, url_for, flash
            flash("Task created successfully", "success")
            return redirect(url_for("tasks.get_task", task_id=document.id))
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Database error: {str(e)}"
        if wants_json():
            return jsonify({"success": False, "error": error_msg}), 500
        else:
            abort(500, description=error_msg)


@bp.route("/", methods=["GET"])
@login_required
@task_access_required
def list_tasks():
    """
    Get list of tasks with role-based filtering.
    
    DUAL RESPONSE ENDPOINT: Returns JSON or HTML based on request headers.
    
    Query parameters:
    - status: Filter by status (pending, in_progress, completed, reviewed, approved, all)
    - limit: Max number of tasks to return (default: 50, max: 100)
    - offset: Pagination offset (default: 0)
    - worker_id: Filter by worker (planner/admin only)
    - container_number: Search by container number
    
    Role-based behavior:
    - Worker: Only sees their assigned tasks
    - Planner/Admin: Sees all tasks (can filter by worker)
    
    JSON Response (200):
    {
        "success": true,
        "tasks": [
            {
                "id": "doc-uuid",
                "container_number": "ABCD1234567",
                "client_name": "ACME Corp",
                "status": "pending",
                "worker": {...},
                "form_type": "desconsolidado",
                "created_at": "2025-10-21T10:00:00Z",
                ...
            }
        ],
        "total": 15,
        "offset": 0,
        "limit": 50,
        "user_role": "worker"
    }
    
    HTML Response:
        Renders 'tasks/list.html' template with task data
    """
    # Get query parameters with defaults and validation
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 items
    offset = int(request.args.get('offset', 0))
    worker_id_filter = request.args.get('worker_id')
    container_search = request.args.get('container_number')
    
    # Start building the query
    # Join necessary tables for complete task information
    # UPDATED: Left join Planification since standalone tasks have NULL planification_id
    query = Document.query.outerjoin(Planification).join(Form)
    
    # Role-based filtering
    if g.user.role == "worker":
        # Workers see tasks assigned to them OR created by them
        query = query.filter(
            db.or_(
                Document.worker_id == g.user.id,
                Document.created_by_id == g.user.id
            )
        )
    elif g.user.role in ["planner", "admin"]:
        # Planners and admins can see all tasks
        # But can optionally filter by worker using query param
        if worker_id_filter:
            query = query.filter(Document.worker_id == worker_id_filter)
    
    # Status filtering
    # 'all' shows every status, otherwise filter to specific status
    if status != 'all':
        query = query.filter(Document.status == status)
    
    # TODO: Implement generic search in record_data JSON field
    # Container/record search would need to search within the JSON field
    # For PostgreSQL, this can be done with JSONB operators:
    # query = query.filter(Document.record_data['field_name'].astext.ilike(f"%{search}%"))
    # For now, this search is disabled to support any form structure
    if container_search:
        # Placeholder: This would need JSON field search implementation
        # Example for PostgreSQL JSONB:
        # query = query.filter(
        #     db.or_(
        #         Document.record_data['container_number'].astext.ilike(f"%{container_search}%"),
        #         Document.record_data['client_name'].astext.ilike(f"%{container_search}%")
        #     )
        # )
        pass
    
    # Get total count BEFORE pagination (for showing "X of Y results")
    total = query.count()
    
    # Apply pagination and execute query
    # Order by creation date (newest first)
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    # Serialize documents to dictionary format
    # This creates a simple data structure that works for both JSON and templates
    # REASONING: Use record_data dynamically to support any form structure
    tasks = []
    for doc in documents:
        task_data = {
            "id": doc.id,
            
            # DYNAMIC RECORD DATA - supports any form type
            # Pass the entire record_data dictionary for flexibility
            # UPDATED: Access directly from document (no longer through record)
            "record_data": doc.record_data or {},
            
            "status": doc.status,
            "worker": {
                "id": doc.worker.id,
                "username": doc.worker.username
            } if doc.worker else None,
            "created_by": {
                "id": doc.created_by.id,
                "username": doc.created_by.username
            } if doc.created_by else None,
            # UPDATED: Access form directly from document (no longer through record.planification)
            "form_type": doc.form.form_type,
            "form_name": doc.form.name,
            "planification_id": doc.planification_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "started_at": doc.started_at.isoformat() if doc.started_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "is_synced": doc.is_synced,
            # Add the Document object itself for HTML template use
            "_document": doc
        }
        tasks.append(task_data)
    
    # DUAL RESPONSE: Check what format the client wants
    if wants_json():
        # JSON Response - for API clients, AJAX, PWA service worker
        return jsonify({
            "success": True,
            "tasks": tasks,
            "total": total,
            "offset": offset,
            "limit": limit,
            "user_role": g.user.role
        }), 200
    
    # HTML Response - for browser clicks
    # Render template with all the data needed for display
    return render_template(
        "tasks/task_list.html",
        tasks=tasks,
        status=status,
        total=total,
        offset=offset,
        limit=limit,
        user=g.user,
        container_search=container_search,
        worker_id_filter=worker_id_filter
    )


@bp.route("/<task_id>", methods=["GET"])
@login_required
@task_access_required
def get_task(task_id):
    """
    Get detailed information about a specific task/document.
    
    DUAL RESPONSE ENDPOINT: Returns JSON or HTML based on request headers.
    
    Returns complete task information including:
    - Document metadata and status
    - Associated record (container) data
    - Form structure with questions
    - Current responses (answers already filled)
    - Photos taken
    
    Access control:
    - Workers: Can only access their own tasks
    - Planners/Admins: Can access any task
    
    JSON Response (200):
    {
        "success": true,
        "task": {
            "id": "doc-uuid",
            "status": "in_progress",
            "container": {...},
            "form": {
                "questions": [...]
            },
            "responses": {...},
            "photos": [...],
            "worker": {...},
            "timestamps": {...}
        }
    }
    
    HTML Response:
        Renders 'tasks/detail.html' template with form for editing
    
    JSON Error Response (404):
    {
        "success": false,
        "error": "Task not found"
    }
    
    JSON Error Response (403):
    {
        "success": false,
        "error": "Access denied. You can only view your own tasks."
    }
    """
    # Query the document with ALL related data using joinedload
    # joinedload = eager loading strategy (gets everything in one query)
    # This is more efficient than lazy loading which would cause N+1 queries
    # UPDATED: Removed Record join - Document now directly references Planification and Form
    document = Document.query.options(
        db.joinedload(Document.form).joinedload(Form.questions),  # Direct form access
        db.joinedload(Document.planification),  # Optional planification (might be NULL)
        db.joinedload(Document.worker)  # Worker info
    ).filter_by(id=task_id).first()  

    # 404 if task doesn't exist
    if not document:
        if wants_json():
            return jsonify({
                "success": False,
                "error": "Task not found"
            }), 404
        else:
            abort(404)
    
    # Permission check: Workers can only see their own tasks
    if g.user.role == "worker" and document.worker_id != g.user.id:
        if wants_json():
            return jsonify({
                "success": False,
                "error": "Access denied. You can only view your own tasks."
            }), 403
        else:
            abort(403)
    
    # Serialize form questions
    # Sort by order field to display questions in correct sequence
    # UPDATED: Access form directly from document (no longer through record.planification)
    questions = []
    for q in sorted(document.form.questions, key=lambda x: x.order):
        questions.append({
            "id": q.id,
            "text": q.question_text,
            "type": q.question_type,
            "is_required": q.is_required,
            "order": q.order,
            "options": q.options or {},
            # Add Question object for HTML template
            "_question": q
        })
    
    # Build complete task data structure
    # REASONING: Use record_data dynamically instead of hardcoded fields
    # This allows the system to work with ANY form structure, not just container forms
    # record_data is a flexible JSON field that adapts to different form types
    task_data = {
        "id": document.id,
        "status": document.status,
        
        # DYNAMIC RECORD DATA - works with any form structure
        # Instead of hardcoded fields, we pass the entire record_data dictionary
        # The template will display whatever fields exist in this specific record
        # UPDATED: Access directly from document (no longer through record)
        "record_data": document.record_data or {},
        
        # Form structure with questions
        # UPDATED: Access form directly from document (no longer through record.planification)
        "form": {
            "id": document.form.id,
            "name": document.form.name,
            "type": document.form.form_type,
            "questions": questions
        },
        "responses": document.responses or {},
        "photos": document.photos or [],
        "worker": {
            "id": document.worker.id,
            "username": document.worker.username
        } if document.worker else None,
        "timestamps": {
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "started_at": document.started_at.isoformat() if document.started_at else None,
            "completed_at": document.completed_at.isoformat() if document.completed_at else None,
            "synced_at": document.synced_at.isoformat() if document.synced_at else None
        },
        "is_synced": document.is_synced,
        # Add Document object for HTML template
        "_document": document
    }
    
    # DUAL RESPONSE: Check what format the client wants
    if wants_json():
        # JSON Response - for API clients
        return jsonify({
            "success": True,
            "task": task_data
        }), 200
    
    # HTML Response - render form for filling/editing
    return render_template(
        "tasks/task_detail.html",
        task=task_data,
        user=g.user
    )


@bp.route("/<task_id>/update", methods=["PUT", "PATCH"])
@login_required
@task_access_required
def update_task(task_id):
    """
    Update a task's data (save form progress or change status).
    
    JSON-ONLY ENDPOINT: This endpoint only accepts and returns JSON.
    It's designed for AJAX calls and PWA offline sync.
    
    This endpoint handles:
    1. Form progress saves (workers filling forms)
    2. Status changes (starting, completing, reviewing)
    3. Photo additions
    4. Offline sync (is_synced flag)
    
    JSON Request Body:
    {
        "status": "in_progress",  // Optional: Change status
        "responses": {             // Optional: Form field answers
            "question-uuid": "answer value",
            ...
        },
        "photos": [               // Optional: Photo references
            {
                "question_id": "photo-q-uuid",
                "path": "/uploads/photo123.jpg",
                "timestamp": "2025-10-21T12:30:00Z"
            }
        ],
        "mark_synced": true       // Optional: Mark as synced after offline update
    }
    
    Access control:
    - Workers: Can update only their own assigned tasks
    - Planners/Admins: Can update any task
    
    JSON Success Response (200):
    {
        "success": true,
        "message": "Task updated successfully",
        "task": {
            "id": "task-uuid",
            "status": "in_progress",
            "updated_at": "2025-10-21T11:45:00Z",
            "is_synced": true
        }
    }
    
    JSON Error Response (400):
    {
        "success": false,
        "error": "Invalid status value"
    }
    """
    # This endpoint MUST receive JSON
    # HTML forms should use a different route (to be implemented)
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json"
        }), 400
    
    # Get the document
    document = Document.query.filter_by(id=task_id).first()
    
    if not document:
        return jsonify({
            "success": False,
            "error": "Task not found"
        }), 404
    
    # Permission check: Workers can only update their own tasks
    if g.user.role == "worker" and document.worker_id != g.user.id:
        return jsonify({
            "success": False,
            "error": "Access denied. You can only update your own tasks."
        }), 403
    
    data = request.get_json()
    
    # Update status if provided
    if "status" in data:
        new_status = data["status"]
        valid_statuses = ["pending", "in_progress", "completed", "reviewed", "approved"]
        
        if new_status not in valid_statuses:
            return jsonify({
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400
        
        # Handle status transitions with automatic timestamp updates
        old_status = document.status
        document.status = new_status
        
        # Status transition logic
        if new_status == "in_progress" and old_status == "pending":
            # Worker starting the task
            # Auto-assign worker if not already assigned
            if not document.worker_id:
                document.worker_id = g.user.id
            # Set start time on first transition to in_progress
            if not document.started_at:
                document.started_at = datetime.now(timezone.utc)
        
        elif new_status == "completed" and old_status == "in_progress":
            # Worker completing the task
            # Set completion time on first transition to completed
            if not document.completed_at:
                document.completed_at = datetime.now(timezone.utc)
        
        elif new_status == "reviewed":
            # Planner reviewing the task
            # Update review timestamp every time status changes to reviewed
            document.reviewed_at = datetime.now(timezone.utc)
    
    # Update responses (merge with existing responses)
    # This allows incremental form filling - worker can save progress
    if "responses" in data:
        if document.responses is None:
            document.responses = {}
        # Merge new responses with existing ones
        document.responses.update(data["responses"])
        # Mark as modified for SQLAlchemy to detect JSON field change
        # Without this, SQLAlchemy might not detect the change
        db.session.query(Document).filter_by(id=task_id).update(
            {"responses": document.responses},
            synchronize_session=False
        )
    
    # Update photos (append to existing photos list)
    # Photos are added, never removed (audit trail)
    if "photos" in data:
        if document.photos is None:
            document.photos = []
        # Append new photos to existing list
        document.photos.extend(data["photos"])
        # Mark as modified for SQLAlchemy
        db.session.query(Document).filter_by(id=task_id).update(
            {"photos": document.photos},
            synchronize_session=False
        )
    
    # Handle sync flag
    # When offline changes are uploaded, they're marked as synced
    if data.get("mark_synced", False):
        document.is_synced = True
        document.synced_at = datetime.now(timezone.utc)
    else:
        # Any update marks as not synced (needs to be sent to other clients)
        document.is_synced = False
    
    # Update modification timestamp
    document.updated_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Task updated successfully",
            "task": {
                "id": document.id,
                "status": document.status,
                "updated_at": document.updated_at.isoformat(),
                "is_synced": document.is_synced
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Database error: {str(e)}"
        }), 500


@bp.route("/sync/status", methods=["GET"])
@login_required
@task_access_required
def sync_status():
    """
    Get sync status for offline-first PWA.
    
    JSON-ONLY ENDPOINT: Returns sync information for offline data reconciliation.
    
    This endpoint allows PWA to:
    1. Compare last_sync with server changes
    2. Download updated tasks
    3. Upload local changes
    4. Resolve conflicts
    
    Query Parameters:
    - last_sync (optional): ISO timestamp of last successful sync
    
    Example: GET /tasks/sync/status?last_sync=2025-10-21T12:00:00Z
    
    JSON Response (200):
    {
        "success": true,
        "server_time": "2025-10-21T13:00:00+00:00",
        "needs_sync": {
            "tasks_updated": [
                {
                    "id": "task-uuid-1",
                    "updated_at": "2025-10-21T12:30:00+00:00",
                    "status": "in_progress"
                }
            ],
            "tasks_assigned": [
                {
                    "id": "task-uuid-3",
                    "assigned_at": "2025-10-21T12:00:00+00:00"
                }
            ],
            "tasks_removed": []
        },
        "sync_conflicts": []
    }
    """
    last_sync_str = request.args.get('last_sync')
    last_sync = None
    
    if last_sync_str:
        try:
            # Parse ISO 8601 timestamp
            # Replace 'Z' with '+00:00' for Python's datetime parser
            last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid last_sync format. Use ISO 8601 format."
            }), 400
    
    # Build query based on user role
    if g.user.role == "worker":
        base_query = Document.query.filter_by(worker_id=g.user.id)
    else:
        # Planners and admins see all documents
        base_query = Document.query
    
    # Tasks updated since last sync
    tasks_updated = []
    if last_sync:
        # Find documents modified on server after last sync
        # is_synced filter ensures we only get server-side changes
        # (not echoing back changes the client just uploaded)
        updated_docs = base_query.filter(
            Document.updated_at > last_sync,
            Document.is_synced  # Only server-side changes
        ).all()
        
        for doc in updated_docs:
            tasks_updated.append({
                "id": doc.id,
                "updated_at": doc.updated_at.isoformat(),
                "status": doc.status
            })
    
    # New assignments since last sync (worker only)
    tasks_assigned = []
    if g.user.role == "worker" and last_sync:
        # Find tasks newly assigned to this worker
        newly_assigned = Document.query.filter(
            Document.worker_id == g.user.id,
            Document.created_at > last_sync
        ).all()
        
        for doc in newly_assigned:
            tasks_assigned.append({
                "id": doc.id,
                "assigned_at": doc.created_at.isoformat()
            })
    
    # Detect conflicts (documents modified both locally and on server)
    # This would require tracking client-side modification timestamps
    # For now, return empty array (to be implemented with client metadata)
    sync_conflicts = []
    
    return jsonify({
        "success": True,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "needs_sync": {
            "tasks_updated": tasks_updated,
            "tasks_assigned": tasks_assigned,
            "tasks_removed": []  # To be implemented: track deleted tasks
        },
        "sync_conflicts": sync_conflicts
    }), 200